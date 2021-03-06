try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements
from codecs import open
from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
requirements = parse_requirements(os.path.join(here, 'requirements.txt'), session='hack')

about = {}
with open(os.path.join(here, 'pyghost', '__version__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)

setup(
    name='pyghost',
    description=about['__description__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    license=about['__license__'],
    python_requires='>=3.4',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[str(ir.req) for ir in requirements],
)
