from setuptools import setup

import versioneer

install_requires = [
    'aiosmtpd',
    'chardet',
    'click',
    'dnspython',
    'lmtpd>=4,<7.0.0',
    'python-daemon>2.2.0',
]

extras_require = {
    "docs": [
        "sphinx",
        "sphinx_rtd_theme",
        "sphinx-click",
    ],
}

config = {
    'description': 'A Python Mail Server',
    'long_description': open("README.rst").read(),
    'url': 'https://github.com/moggers87/salmon',
    'download_url': 'http://pypi.python.org/pypi/salmon-mail',
    'author': 'Salmon project contributors',
    'maintainer': 'Matt Molyneaux',
    'maintainer_email': 'moggers87+git@moggers87.co.uk',
    'version': versioneer.get_version(),
    'cmdclass': versioneer.get_cmdclass(),
    'install_requires': install_requires,
    'extras_require': extras_require,
    'test_suite': 'tests',
    'packages': ['salmon', 'salmon.handlers'],
    'include_package_data': True,
    'name': 'salmon-mail',
    'license': 'GPLv3',
    'classifiers': [
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        'Topic :: Communications :: Email',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        ],
    'python_requires': '>=3.5',
    'entry_points': {
        'console_scripts':
            ['salmon = salmon.commands:main'],
    },
}

setup(**config)
