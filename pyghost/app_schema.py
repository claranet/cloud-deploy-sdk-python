from schema import And, Optional, Regex, Schema


APPLICATION_ID_SCHEMA = Schema(And(str, Regex(r'[a-f0-9]{24}')))

APPLICATION_SCHEMA = Schema({
    'name': And(str, Regex(r'^[a-zA-Z0-9_.+-]*$')),
    'env': And(str, Regex(r'^[a-z0-9\-\_]*$')),
    'role': And(str, Regex(r'^[a-z0-9\-\_]*$')),
    Optional('description'): str,
    Optional('region'): str,

    'vpc_id': And(str, Regex(r'^vpc-[a-z0-9]*$')),

    Optional('assumed_account_id'): str,
    Optional('assumed_region_name'): str,
    Optional('assumed_role_name'): str,

    Optional('instance_type'): str,
    Optional('instance_monitoring', default=False): bool,

    Optional('autoscale'): {
        Optional('name'): str,
        Optional('enable_metrics', default=False): bool,
        Optional('min'): And(int, lambda n: n > 0),
        Optional('max'): And(int, lambda n: n > 0)
    },

    'build_infos': {
        Optional('ssh_username', default='admin'): And(str, Regex(r'^[a-z\_][a-z0-9\_\-]{0,30}$')),
        'source_ami': And(str, Regex(r'^ami-[a-z0-9]*$')),
        'subnet_id': And(str, Regex(r'^subnet-[a-z0-9]*$')),
        Optional('source_container_image'): str
    },

    'environment_infos': {
        Optional('instance_profile'): And(str, Regex(r'^[a-zA-Z0-9\+\=\,\.\@\-\_]{1,128}$')),
        Optional('key_name'): And(str, Regex(r'^[a-zA-Z0-9\.\-\_]{1,255}$')),
        Optional('public_ip_address', default=True): bool,

        Optional('root_block_device'): {
            Optional('size', default=20): And(int, lambda n: n >= 20),
            Optional('name'): And(str, Regex(r'^$|^(/[a-z0-9]+/)?[a-z0-9]+$'))
        },

        Optional('security_groups'): [And(str, Regex(r'^sg-[a-z0-9]*$'))],

        Optional('instance_tags'): [{
            'tag_name': str,
            'tag_value': str
        }],

        Optional('subnet_ids'): [And(str, Regex(r'^subnet-[a-z0-9]*$'))],

        Optional('optional_volumes'): [{
            'device_name': And(str, Regex(r'^/dev/xvd[b-m]$')),
            'volume_type': And(str, lambda s: s in ['gp2', 'io1', 'standard', 'st1', 'sc1']),
            'volume_size': int,
            Optional('iops'): int,
            Optional('launch_block_device_mappings'): bool
        }]
    },

    Optional('environment_variables'): [{
        'key': And(str, Regex(r'^[a-zA-Z_]+[a-zA-Z0-9_]*$')),
        'value': str
    }],

    Optional('env_vars'): [{
        'var_key': And(str, Regex(r'^[a-zA-Z_]+[a-zA-Z0-9_]*$')),
        'var_value': str
    }],

    Optional('log_notifications'): [{
        'email': And(str, Regex(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')),
        'job_states': [And(str, lambda s: s in ['*', 'done', 'failed', 'aborted'])],
    }],

    Optional('blue_green'): {
        Optional('enable_blue_green'): bool,
        Optional('color'): And(str, lambda s: s in ['blue', 'green']),
        Optional('is_online'): bool,

        Optional('hooks'): {
            Optional('post_swap'): str,
            Optional('pre_swap'): str
        },

        Optional('alter_ego_id'): str
    },

    Optional('features'): [{
        'name': And(str, Regex(r'^[a-zA-Z0-9\.\-\_]*$')),
        Optional('version'): And(str, Regex(r'^[a-zA-Z0-9\.\-\_\/:~\+=\,]*$')),
        'provisioner': And(str, lambda s: s in ['ansible', 'salt']),
        Optional('parameters'): object
    }],

    Optional('lifecycle_hooks'): {
        Optional('pre_buildimage'): str,
        Optional('post_buildimage'): str,
        Optional('pre_bootstrap'): str,
        Optional('post_bootstrap'): str
    },

    'modules': [{
        'name': And(str, Regex(r'^[a-zA-Z0-9\.\-\_]*$')),
        Optional('git_repo'): str,
        Optional('source'): {
            Optional('protocol', default='git'): And(str, lambda s: s in ['git', 's3']),
            Optional('url'): str,
            Optional('mode', default='symlink'): And(str, lambda s: s in ['symlink']),
        },
        'path': And(str, Regex(r'^(/[a-zA-Z0-9\.\-\_]+)+$')),
        'scope': And(str, lambda s: s in ['system', 'code']),
        Optional('uid', default=0): And(int, lambda n: n >= 0),
        Optional('gid', default=0): And(int, lambda n: n >= 0),
        Optional('build_pack'): str,
        Optional('pre_deploy'): str,
        Optional('post_deploy'): str,
        Optional('after_all_deploy'): str
    }],

    Optional('safe-deployment'): {
        Optional('ha_backend'): str,
        Optional('load_balancer_type', default='elb'): And(str, lambda s: s in ['elb', 'alb', 'haproxy']),
        Optional('app_tag_value'): str,
        Optional('api_port'): int,
        Optional('wait_before_deploy', default=10): And(int, lambda n: n > 0),
        Optional('wait_after_deploy', default=10): And(int, lambda n: n > 0)
    }
})
