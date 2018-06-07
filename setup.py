try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements
from setuptools import setup, find_packages

requirements = parse_requirements('requirements.txt', session='hack')

CURRENT_VERSION = "v0.1"

setup(
    name='cloud-deploy-sdk-python',
    description='This is a Python3 SDK/API client for Cloud Deploy (Ghost project).',
    version=CURRENT_VERSION,
    python_requires='>=3.4',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[str(ir.req) for ir in requirements],
)
