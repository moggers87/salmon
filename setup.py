
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'package_data': {
        'salmon': ['data/prototype.zip']
    },
    'description': 'A Python mail server forked from Lamson',
    'long_description': 'Salmon is a modern Pythonic mail server built like a web application server.',
    'author': 'Zed A. Shaw',
    'url': 'http://pypi.python.org/pypi/salmon-mail',
    'download_url': 'http://pypi.python.org/pypi/salmon-mail',
    'maintainer': 'Matt Molyneaux',
    'maintainer_email': 'moggers87+git@moggers87.co.uk',
    'version': '0',
    'scripts': ['bin/salmon'],
    'install_requires': ['chardet','jinja2','mock','nose','python-daemon','python-modargs','lmtpd'],
    'packages': ['salmon', 'salmon.handlers'],
    'name': 'salmon-mail',
    'license': 'GPLv3',
    'classifiers': [
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2',
        'Intended Audience :: Developers',
        'Topic :: Communications :: Email',
        'Topic :: Software Development :: Libraries :: Application Frameworks']
}

setup(**config)
