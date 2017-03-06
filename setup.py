import os
import subprocess

from setuptools import setup

# Prefer to use the version from the Debian package. Fall back to the version
# from git. This way the .git directory does not have to be included in the
# Debian source package.
if os.path.exists('debian/changelog'):
    for line in subprocess.check_output(['dpkg-parsechangelog']).decode().split('\n'):
        tokens = line.split()
        if tokens[0] == 'Version:':
            version = tokens[1]
            break
else:
    build_no = os.environ.get('BUILD_NUMBER', 'dev0')
    git_ref = subprocess.check_output(['git', 'rev-parse', '--verify', '--short', 'HEAD']).decode().rstrip()
    version = '0.{}+g{}'.format(build_no, git_ref)

setup(
    name = 'temper-exporter',
    version = version,
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
        'pyudev',
        'setuptools',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require = [
        'pytest',
        'pytest-mock',
    ],
    entry_points = {
        'console_scripts': [
            'temper-exporter = temper_exporter:main',
        ],
    },
)
