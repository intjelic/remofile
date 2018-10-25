from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='remofile',
    version='1.0.0.dev5',
    packages=[
        'remofile'
    ],
    description='Quick and easy-to-use alternative to FTP',
    long_description=long_description,
    long_description_content_type='text/markdown',
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
        'Source'       : 'https://github.com/sonkun/remofile/',
        'Tracker'      : 'https://github.com/sonkun/remofile/issues',
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
