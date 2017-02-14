import subprocess

from setuptools import setup

try:
    git_ref = subprocess.check_output(['git', 'rev-parse', '--verify', '--short', 'HEAD']).decode().rstrip()
except:
    git_ref = '?'

setup(
    name = 'temper-exporter',
    version = '0+g{}'.format(git_ref),
    description = 'Prometheus exporter for PCSensor TEMPer sensor devices',
    url = 'https://github.com/yrro/temper-exporter',
    author = 'Sam Morris',
    author_email = 'sam@robots.org.uk',
    license = 'MIT',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Environment :: No Input/Output (Daemon)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: System :: Monitoring',
    ],
    keywords = 'prometheus monitoring temperature sensor temper',
    packages = ['temper_exporter'],
    install_requires = [
        'prometheus_client',
        'setuptools'
    ],
    entry_points = {
        'console_scripts': [
            'temper-exporter = temper_exporter:main',
        ],
    },
)
