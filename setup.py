import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

install_requires = [
    'argparse',
    'chardet',
    'lmtpd>=4',
    'pydns',
]

if sys.platform != 'win32':  # Can daemonize
    install_requires.append('python-daemon<1.7')
else:
    install_requires.append('lockfile')

test_requires = [
    'coverage',
    'jinja2',
    'mock',
]

config = {
    'description': 'A Python mail server forked from Lamson',
    'long_description': 'Salmon is a modern Pythonic mail server built like a web application server.',
    'author': 'Zed A. Shaw',
    'url': 'https://github.com/moggers87/salmon',
    'download_url': 'http://pypi.python.org/pypi/salmon-mail',
    'maintainer': 'Matt Molyneaux',
    'maintainer_email': 'moggers87+git@moggers87.co.uk',
    'version': '2',
    'install_requires': install_requires,
    'tests_require': test_requires,
    'setup_requires': ['nose'],
    'test_suite': 'nose.collector',
    'packages': ['salmon', 'salmon.handlers'],
    'include_package_data': True,
    'name': 'salmon-mail',
    'license': 'GPLv3',
    'classifiers': [
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Intended Audience :: Developers',
        'Topic :: Communications :: Email',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
        ],
    "entry_points": {
        'console_scripts':
            ['salmon = salmon.commands:main'],
    },
}

setup(**config)
