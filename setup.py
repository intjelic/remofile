from setuptools import setup

long_description = """Remofile is a protocol, a Python library and a \
command-line interface to transfer files back and forth from/to a \
remote server. It's an embeddable and easy-to-use alternative to FTP \
and other transfer files tools.
"""

setup(
    name='remofile',
    version='1.0.0.dev1',
    packages=[
        'remofile'
    ],
    description='Easy-to-use and embeddable alternative to FTP',
    long_description=long_description,
    long_description_content_type='text/plain',
    url='https://www.sonkun-dev.net/project/remofile',
    author='Jonathan De Wachter',
    author_email='dewachter.jonathan@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Communications :: File Sharing',
        'Topic :: Desktop Environment :: File Managers',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
        'Topic :: System :: Filesystems',
    ],
    keywords='remofile file transfer ftp alternative quick embeddable secure protocol',
    project_urls={
        'Documentation': 'http://remofile.readthedocs.io',
        'Source': 'https://github.com/sonkun/remofile/',
        'Tracker': 'https://github.com/sonkun/remofile/issues',
    },
    install_requires=[
        'Click',
        'pyzmq',
        'shortuuid'
    ],
    python_requires='>=3.6',
    entry_points='''
        [console_scripts]
        remofile=remofile.cli:cli
        rmf=remofile.cli:cli
    ''',
    test_suite="tests"
)
