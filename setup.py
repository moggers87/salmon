from setuptools import setup


install_requires = [
    'chardet',
    'dnspython',
    'lmtpd>=4',
    'python-daemon',
    'six',
]

test_requires = [
    'coverage',
    'jinja2',
    'mock',
]

config = {
    'description': 'A Python mail server forked from Lamson',
    'long_description': open("README.rst").read(),
    'url': 'https://github.com/moggers87/salmon',
    'download_url': 'http://pypi.python.org/pypi/salmon-mail',
    'author': 'Zed A. Shaw',
    'maintainer': 'Matt Molyneaux',
    'maintainer_email': 'moggers87+git@moggers87.co.uk',
    'version': '3.0.1',
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'Topic :: Communications :: Email',
        'Topic :: Software Development :: Libraries :: Application Frameworks'
        ],
    'entry_points': {
        'console_scripts':
            ['salmon = salmon.commands:main'],
    },
}

setup(**config)
