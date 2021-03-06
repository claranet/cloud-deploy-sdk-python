import base64
import copy
import json
import os
import time
import urllib.parse
from base64 import b64encode
from enum import Enum

import requests
from socketIO_client import SocketIO

from .app_schema import APPLICATION_SCHEMA, APPLICATION_ID_SCHEMA
from .utils import trim_xml_html_tags, trim_ansi_tags

DEFAULT_HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}

DEFAULT_PAGE_SIZE = 20

METHOD_GET = 'get'
METHOD_POST = 'post'
METHOD_PATCH = 'patch'

RETURN_TYPE_PLAIN = 'plain'
RETURN_TYPE_JSON = 'json'

DEPLOYMENT_STRATEGY_SERIAL = 'serial'
DEPLOYMENT_STRATEGY_PARALLEL = 'parallel'
DEPLOYMENT_STRATEGIES = (DEPLOYMENT_STRATEGY_SERIAL, DEPLOYMENT_STRATEGY_PARALLEL)

SCRIPT_EXECUTION_STRATEGY_SINGLE = 'single'
SCRIPT_EXECUTION_STRATEGY_SERIAL = 'serial'
SCRIPT_EXECUTION_STRATEGY_PARALLEL = 'parallel'
SCRIPT_EXECUTION_STRATEGIES = (
    SCRIPT_EXECUTION_STRATEGY_SINGLE, SCRIPT_EXECUTION_STRATEGY_SERIAL, SCRIPT_EXECUTION_STRATEGY_PARALLEL)

SAFE_DEPLOYMENT_STRATEGY_ONE_BY_ONE = '1by1'
SAFE_DEPLOYMENT_STRATEGY_THIRD = '1/3'
SAFE_DEPLOYMENT_STRATEGY_QUARTER = '25%'
SAFE_DEPLOYMENT_STRATEGY_HALF = '50%'
SAFE_DEPLOYMENT_STRATEGIES = (SAFE_DEPLOYMENT_STRATEGY_ONE_BY_ONE, SAFE_DEPLOYMENT_STRATEGY_THIRD,
                              SAFE_DEPLOYMENT_STRATEGY_QUARTER, SAFE_DEPLOYMENT_STRATEGY_HALF)

BLUEGREEN_SWAP_STRATEGY_OVERLAP = 'overlap'
BLUEGREEN_SWAP_STRATEGY_ISOLATED = 'isolated'
BLUEGREEN_SWAP_STRATEGIES = (BLUEGREEN_SWAP_STRATEGY_OVERLAP, BLUEGREEN_SWAP_STRATEGY_ISOLATED)

ROLLING_UPDATE_STRATEGY_ONE_BY_ONE = '1by1'
ROLLING_UPDATE_STRATEGY_THIRD = '1/3'
ROLLING_UPDATE_STRATEGY_QUARTER = '25%'
ROLLING_UPDATE_STRATEGY_HALF = '50%'
ROLLING_UPDATE_STRATEGIES = (ROLLING_UPDATE_STRATEGY_ONE_BY_ONE, ROLLING_UPDATE_STRATEGY_THIRD,
                             ROLLING_UPDATE_STRATEGY_QUARTER, ROLLING_UPDATE_STRATEGY_HALF)


class JobStatuses(Enum):
    def __str__(self):
        return str(self.value)

    INIT = 'init'
    STARTED = 'started'
    CANCELLED = 'cancelled'
    DONE = 'done'
    FAILED = 'failed'
    ABORTED = 'aborted'


class JobCommands(Enum):
    def __str__(self):
        return str(self.value)

    BUILDIMAGE = 'buildimage'
    CREATEINSTANCE = 'createinstance'
    DEPLOY = 'deploy'
    DESTROYALLINSTANCES = 'destroyallinstances'
    EXECUTESCRIPT = 'executescript'
    PREPAREBLUEGREEN = 'preparebluegreen'
    PURGEBLUEGREEN = 'purgebluegreen'
    RECREATEINSTANCES = 'recreateinstances'
    REDEPLOY = 'redeploy'
    SWAPBLUEGREEN = 'swapbluegreen'
    UPDATEAUTOSCALING = 'updateautoscaling'
    UPDATELIFECYCLEHOOKS = 'updatelifecyclehooks'
    DESTROYINSTANCE = 'destroyinstance'
    ROLLBACK = 'rollback'


class ApiClientException(Exception):
    pass


class ApiClient(object):
    path = None

    def __init__(self, host, username, password):
        """
        Creates an API client instance
        :param host: str: host for API
        :param username: str: username for API
        :param password: str: password for API
        """
        self.host = host
        self.username = username
        self.password = password

    @staticmethod
    def _clean_dict_object(obj):
        """
        Clean some internal attributes of an object
        :param obj: dict:
        :return: dict:
        """
        for attr in ['_latest_version', '_links', '_version']:
            if attr in obj:
                del obj[attr]
        return obj

    def _get_url(self, path, params, object_id=None):
        """
        Construct the API URL
        :param path: str:
        :param params: dict:
        :param object_id: str:
        :return: str:
        """
        base_url = urllib.parse.urljoin(self.host, path)
        if object_id:
            base_url = urllib.parse.urljoin(base_url, object_id)
        if params:
            return "{}?{}".format(base_url, urllib.parse.urlencode(params, safe=':'))
        return base_url

    def _do_request(self, path, object_id=None, body=None, params=None,
                    method=METHOD_GET, return_type=RETURN_TYPE_JSON, headers=None):
        """
        Do the API requests
        :param path: str:
        :param object_id: str:
        :param body: dict:
        :param params: dict:
        :param method: str:
        :param return_type: str:
        :param headers: dict:
        :return: dict:
        """
        if headers is None:
            headers = {}
        url = self._get_url(path, params, object_id)
        try:
            response = requests.request(method, url,
                                        json=body,
                                        auth=(self.username, self.password),
                                        headers={**DEFAULT_HEADERS, **headers})
            if response.status_code >= 300:
                raise ApiClientException(
                    'Error while calling Cloud Deploy : [{}] {}'.format(response.status_code, response.text))
            if return_type == RETURN_TYPE_JSON:
                ret = response.json()
            else:
                ret = response.text
        except requests.ConnectionError as e:
            raise ApiClientException('Error while sending request to {}'.format(url)) from e
        except ValueError as e:
            raise ApiClientException('Error while reading response from {}'.format(url)) from e
        return ret

    def _do_retrieve(self, path, object_id, **extra_params):
        """
        Do the retrieve API call
        :param path: str:
        :param object_id: str:
        :param extra_params: dict:
        :return: dict:
        """
        data = self._do_request(path, object_id, params=extra_params)
        return self._clean_dict_object(data)

    def _do_list(self, path, nb, page, sort, **extra_params):
        """
        Do the list API call
        :param path: str:
        :param nb: int:
        :param page: int:
        :param sort: str:
        :param extra_params: dict:
        :return: tuple: (data_list, data_results_per_page, data_total_items, data_current_page)
        """
        params = copy.deepcopy(extra_params)
        params.update({'max_results': nb, 'page': page, 'sort': sort})
        data = self._do_request(path, params=params)
        return ([self._clean_dict_object(item) for item in data['_items']],
                data['_meta']['max_results'], data['_meta']['total'], data['_meta']['page'])

    def _do_create(self, path, obj, **extra_params):
        """
        Do the create API call
        :param path: str:
        :param obj: dict:
        :param extra_params: dict:
        :return: str:
        """
        data = self._do_request(path, body=obj, params=extra_params, method=METHOD_POST)
        return data.get('_id')

    def _do_update(self, path, obj, etag, headers=None, **extra_params):
        """
        Do the update API call
        :param path: str:
        :param obj: dict:
        :param etag: string ID:
        :param headers: dict:
        :param extra_params: dict:
        :return: str:
        """
        obj_id = obj.get('_id', None)
        if obj_id is None:
            raise ValueError("'_id' attribute must be set on your object.")
        if headers is None:
            headers = {}
        headers['If-Match'] = etag
        data = self._do_request(os.path.join(path, obj_id), body=obj, params=extra_params,
                                method=METHOD_PATCH, headers=headers)
        return data.get('_id')

    def retrieve(self, object_id):
        """
        Retrieve an object
        :param object_id: str: id of the object
        :return: dict:
        """
        if not self.path:
            raise NotImplementedError('`path` variable must be defined')
        return self._do_retrieve(self.path, object_id)

    def list(self, nb=DEFAULT_PAGE_SIZE, page=1, sort='-_updated'):
        """
        List objects
        :param nb: int: the number of objects to list
        :param page: int: the page to fetch
        :param sort: str: the object order
        :return: tuple: returns the tuple (objects, number of results, total number of objects, page fetched)
        """
        if not self.path:
            raise NotImplementedError('`path` variable must be defined')
        return self._do_list(self.path, nb, page, sort)

    def create(self, obj):
        """
        Create an object
        :param obj: dict: the object
        :return: str: id of the created object
        """
        if not self.path:
            raise NotImplementedError('`path` variable must be defined')
        return self._do_create(self.path, obj)

    def get_version(self):
        """
        Return Cloud Deploy running version
        :return: dict: API version or git branch/tag
        """
        try:
            return self._do_request('/version')
        except:
            return {
                'current_revision_date': '',
                'current_revision_name': 'unknown',
                'current_revision': 'unknown'
            }


class AppsApiClient(ApiClient):
    path = '/apps/'

    def list(self, nb=DEFAULT_PAGE_SIZE, page=1, sort='-_updated', name=None, env=None, role=None):
        """
        List objects
        :param nb: int: the number of objects to list
        :param page: int: the page to fetch
        :param sort: str: the object order
        :param name: str: filter to apply on application name
        :param env: str: filter to apply on application env
        :param role: str: filter to apply on application role
        :return: tuple: returns the tuple (objects, number of results, total number of objects, page fetched)
        """
        query = []
        if role is not None:
            query.append('"role":"{role}"'.format(role=role))
        if env is not None:
            query.append('"env":"{env}"'.format(env=env))
        if name is not None:
            query.append('"name":{{"$regex":"{name}"}}'.format(name=name))
        return self._do_list(self.path, nb, page, sort, where='{' + ",".join(query) + '}')

    def create(self, obj):
        """
        Create an object
        :param obj: dict: the object
        :return: str: id of the created object
        """
        if not self.path:
            raise ValueError('`path` variable must be defined')
        return self._do_create(self.path, obj)

    def update(self, obj, etag):
        """
        Update an object
        :param obj: dict: the object
        :param etag: str: the application etag
        :return: str: id of the updated object
        """
        if not self.path:
            raise ValueError('`path` variable must be defined')
        return self._do_update(self.path, obj, etag)

    def validate_schema(self, app, check_id=False):
        """
        Validate an application schema
        :param app: dict: the application schema
        :param check_id: bool: check application id
        :return: str|bool: id of the updated schema
        """
        if check_id:
            check_id = app['_id']
            del app['_id']
        APPLICATION_SCHEMA.validate(app)
        if check_id:
            APPLICATION_ID_SCHEMA.validate(check_id)
        return check_id or app.get('_id')


def get_applist_join_query(apps_api, application_name, role, env):
    """
    Helper function to generate a query value, get all related application
    :param apps_api: AppsApiClient instance
    :param application_name: query app name filter
    :param role: query role filter
    :param env: query env filter
    """
    app_list, _, _, _ = apps_api.list(name=application_name, role=role, env=env)
    applications = [
        json.dumps({"app_id": application['_id']})
        for application in app_list
    ]
    if len(applications) > 0:
        return '[{}]'.format(','.join(applications))
    else:
        return '[{"app_id": "null"}]'


class JobsApiClient(ApiClient):
    path = '/jobs/'

    def list(self, nb=DEFAULT_PAGE_SIZE, page=1, sort='-_updated',
             application=None, env=None, role=None, command=None, status=None, user=None):
        query = {}

        if application or env or role:
            apps_api = AppsApiClient(self.host, self.username, self.password)
            query['$or'] = get_applist_join_query(apps_api, application, role, env)

        if command:
            query['command'] = '"{}"'.format(command)

        if status:
            query['status'] = '"{}"'.format(status)

        if user:
            query['user'] = '"{}"'.format(user)

        querystr = '{' + ','.join('"{key}":{value}'.format(key=key, value=value) for key, value in query.items()) + '}'
        return self._do_list(self.path, nb, page, sort, embedded='{"app_id":1}', where=querystr)

    def command_buildimage(self, application_id, instance_type=None, skip_bootstrap=None):
        """
        Creates a `buildimage` job
        :param application_id: str: Application ID
        :param instance_type: str: Instance type
        :param skip_bootstrap: bool: Skip provisioner bootstrap
        :return: str: id of the created job
        """
        job = {
            "command": "buildimage",
            "app_id": application_id,
            "options": [],
        }
        if instance_type:
            job["instance_type"] = instance_type
        if skip_bootstrap is not None:
            job["options"].append(str(skip_bootstrap))
        return self.create(job)

    def command_deploy(self, application_id, modules,
                       deployment_strategy=DEPLOYMENT_STRATEGY_SERIAL, safe_deployment_strategy=None):
        """
        Creates a `deploy` job
        :param application_id: str: Application ID
        :param modules: array: list of modules as `{"name": name, "rev": rev}`
        :param deployment_strategy: str: Deployment strategy
        :param safe_deployment_strategy: str: Safe deployment strategy to use
        :return: str: id of the created job
        """
        job = {
            "command": "deploy",
            "app_id": application_id,
            "modules": modules,
            "options": [deployment_strategy or DEPLOYMENT_STRATEGY_SERIAL],
        }
        if safe_deployment_strategy is not None:
            job["options"].append(safe_deployment_strategy)
        return self.create(job)

    def command_redeploy(self, application_id, deployment_id,
                         deployment_strategy=DEPLOYMENT_STRATEGY_SERIAL, safe_deployment_strategy=None):
        """
        Creates a `redeploy` job
        :param application_id: str: Application ID
        :param deployment_id: str: the previous deployment to replay
        :param deployment_strategy: str: Deployment strategy
        :param safe_deployment_strategy: str: Safe deployment strategy to use
        :return: str: id of the created job
        """
        job = {
            "command": "redeploy",
            "app_id": application_id,
            "options": [deployment_id, deployment_strategy or DEPLOYMENT_STRATEGY_SERIAL],
        }
        if safe_deployment_strategy is not None:
            job["options"].append(safe_deployment_strategy)
        return self.create(job)

    def command_executescript(self, application_id, script_content,
                              execution_strategy=SCRIPT_EXECUTION_STRATEGY_SERIAL,
                              safe_deployment_strategy=SAFE_DEPLOYMENT_STRATEGY_ONE_BY_ONE,
                              instance_ip=None, module_context=None):
        """
        Creates a `executescript` job
        :param application_id: str: Application ID
        :param script_content: str: The script to execute in UTF-8 encoding
        :param execution_strategy: str: The script execution strategy
        :param safe_deployment_strategy: str: The safe deployment strategy if not `single` execution strategy
        :param instance_ip: str: Instance IP on which execute the script if `single` execution strategy
        :param module_context: : str: The name of the module in which folder the script will be executed
        :return: str: id of the created job
        """
        execution_strategy = execution_strategy or SCRIPT_EXECUTION_STRATEGY_SINGLE
        safe_deployment_strategy = safe_deployment_strategy or SAFE_DEPLOYMENT_STRATEGY_ONE_BY_ONE
        if execution_strategy == SCRIPT_EXECUTION_STRATEGY_SINGLE and not instance_ip:
            raise ApiClientException('Instance IP must be specified for "single" script execution strategy')
        if execution_strategy != SCRIPT_EXECUTION_STRATEGY_SINGLE and not safe_deployment_strategy:
            raise ApiClientException(
                'Safe deployment strategy must be specified if not "single" script execution strategy')

        job = {
            "command": "executescript",
            "app_id": application_id,
            "options": [
                b64encode(script_content.replace('\r\n', '\n').encode('utf-8')).decode('utf-8'),
                module_context or '',
                execution_strategy,
                instance_ip if execution_strategy == SCRIPT_EXECUTION_STRATEGY_SINGLE else safe_deployment_strategy,
            ],
        }
        return self.create(job)

    def command_createinstance(self, application_id, subnet_id=None, private_ip_address=None):
        """
        Creates a `createinstance` job
        :param application_id: str: Application ID
        :param subnet_id: str: Subnet ID in which create the instance
        :param private_ip_address: Private IP address of the instance
        :return: str: id of the created job
        """
        if not subnet_id and private_ip_address:
            raise ApiClientException('Subnet ID is mandatory when specifying private IP address for buildimage command')
        job = {
            "command": "createinstance",
            "app_id": application_id,
            "options": [],
        }
        if subnet_id is not None:
            job["options"].append(subnet_id)
        if private_ip_address is not None:
            job["options"].append(private_ip_address)
        return self.create(job)

    def command_destroyallinstances(self, application_id):
        """
        Creates a `destroyallinstances` job
        :param application_id: str: Application ID
        :return: str: id of the created job
        """
        job = {
            "command": "destroyallinstances",
            "app_id": application_id,
            "options": [],
        }
        return self.create(job)

    def command_recreateinstances(self, application_id, strategy=None):
        """
        Creates a `recreateinstances` job
        :param application_id: str: Application ID
        :param strategy: str: Rolling Update strategy
        :return: str: id of the created job
        """
        job = {
            "command": "recreateinstances",
            "app_id": application_id,
            "options": [],
        }
        if strategy is not None:
            job["options"].append(strategy)
        return self.create(job)

    def command_updatelifecyclehooks(self, application_id):
        """
        Creates a `updatelifecyclehooks` job
        :param application_id: str: Application ID
        :return: str: id of the created job
        """
        job = {
            "command": "updatelifecyclehooks",
            "app_id": application_id,
            "options": [],
        }
        return self.create(job)

    def command_updateautoscaling(self, application_id):
        """
        Creates a `updateautoscaling` job
        :param application_id: str: Application ID
        :return: str: id of the created job
        """
        job = {
            "command": "updateautoscaling",
            "app_id": application_id,
            "options": [],
        }
        return self.create(job)

    def command_preparebluegreen(self, application_id, copy_ami=False, attach_elb=True):
        """
        Creates a `preparebluegreen` job
        :param application_id: str: Application ID
        :param copy_ami: bool: Copy AMI from online app
        :param attach_elb: bool: Create a temporary ELB to attach to the Auto Scaling goup
        :return: str: id of the created job
        """
        job = {
            "command": "preparebluegreen",
            "app_id": application_id,
            "options": [str(copy_ami), str(attach_elb)],
        }
        return self.create(job)

    def command_purgebluegreen(self, application_id):
        """
        Creates a `purgebluegreen` job
        :param application_id: str: Application ID
        :return: str: id of the created job
        """
        job = {
            "command": "purgebluegreen",
            "app_id": application_id,
            "options": [],
        }
        return self.create(job)

    def command_swapbluegreen(self, application_id, strategy=BLUEGREEN_SWAP_STRATEGY_OVERLAP):
        """
        Creates a `swapbluegreen` job
        :param application_id: str: Application ID
        :param strategy: str: Blue Green swap strategy
        :return: str: id of the created job
        """
        job = {
            "command": "swapbluegreen",
            "app_id": application_id,
            "options": [strategy],
        }
        return self.create(job)

    def get_logs_async(self, job_id, success_handler, exception_handler, wait_for_start=False, no_color=False):
        """
        Return job logs through callback functions
        :param job_id: str: Job ID
        :param success_handler: function: Success function callback, arguments: log_message
        :param exception_handler: function: Error function callback, arguments: exception
        :param wait_for_start: bool: true if we should wait for the job to start
        :param no_color: bool: false by default, should ASCII chars be stripped
        :return: str: data of the job
        """
        job = self.retrieve(job_id)
        while wait_for_start and job['status'] == JobStatuses.INIT.value:
            time.sleep(3)
            job = self.retrieve(job_id)

        if job['status'] == JobStatuses.INIT.value:
            exception_handler(ApiClientException('The job is not started.'))
        else:
            check_ws = requests.get(urllib.parse.urljoin(self.host, '/socket.io/'))
            if not check_ws.status_code == 200:
                exception_handler(ApiClientException('Websocket server is unavailable.'))
                return

            socket_host = self.host if self.host[-1] != '/' else self.host[0:-1]
            with SocketIO(socket_host, verify=True) as socketIO:
                def callback(args):
                    try:
                        if 'error' in args:
                            exception_handler(ApiClientException(args['error']))
                            return
                        if 'raw' not in args:
                            # Backward compatibility, old API returns HTML data for WebUI
                            data_str = trim_xml_html_tags(args['html'])
                            data_str = data_str + "\n"
                        else:
                            data_str = base64.b64decode(args['raw'])
                        if no_color:
                            data_str = trim_ansi_tags(data_str)
                        success_handler(data_str)
                    except Exception as e:
                        exception_handler(e)

                params = {
                    'log_id': job_id,
                    'last_pos': 0,
                    'raw_mode': True,
                    'auth_token': self._get_websocket_token(job_id)
                }
                socketIO.emit('job_logging', params)
                socketIO.on('job', callback)

                while job['status'] == JobStatuses.STARTED.value:
                    socketIO.wait(seconds=3)
                    job = self.retrieve(job_id)
                socketIO.wait(seconds=3)    # We wait 3 more seconds to be sure to get all the data

    def _get_websocket_token(self, job_id):
        """
        Return a job websocket token
        :param job_id: str: Job ID
        :return: str: websocket token of the job
        """
        path = '/jobs/{}/websocket_token/'.format(job_id)
        try:
            token = self._do_request(path, params={}).get('token', '')
        except:
            token = False
        return token


class DeploymentsApiClient(ApiClient):
    path = '/deployments/'

    def list(self, nb=DEFAULT_PAGE_SIZE, page=1, sort='-timestamp',
             application=None, env=None, role=None, revision=None, module=None):
        query = {}

        if application or env or role:
            apps_api = AppsApiClient(self.host, self.username, self.password)
            query['$or'] = get_applist_join_query(apps_api, application, role, env)

        if revision:
            query['revision'] = '"{}"'.format(revision)

        if module:
            query['module'] = '{{"$regex":".*{m}.*"}}'.format(m=module)

        querystr = '{' + ','.join('"{key}":{value}'.format(key=key, value=value) for key, value in query.items()) + '}'
        return self._do_list(self.path, nb, page, sort, embedded='{"app_id":1,"job_id":1}', where=querystr)
