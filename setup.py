
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'package_data': {
        'salmon': ['data/prototype.zip']
    },
    'description': 'A Python mail server'
    'long_description': 'Salmon is a modern Pythonic mail server built like a web application server.',
    'author': 'Zed A. Shaw',
    #'url': 'http://pypi.python.org/pypi/salmon',
    #'download_url': 'http://pypi.python.org/pypi/salmon',
    'maintainer': 'Matt Molyneaux',
    'maintainer_email': 'moggers87+git@moggers87.co.uk',
    'version': '0',
    'scripts': ['bin/salmon'],
    'install_requires': ['chardet', 'jinja2', 'mock', 'nose', 'python-daemon', 'python-modargs'],
    'packages': ['salmon', 'salmon.handlers'],
    'name': 'salmon',
    'license': 'GPLv3'
}

setup(**config)
