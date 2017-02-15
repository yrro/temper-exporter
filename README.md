temper-exporter
============

Exports readings from various PCsensor TEMPer devices for
[Prometheus](https://prometheus.io/).

[![Build Status](https://travis-ci.org/yrro/temper-exporter.svg?branch=master)](https://travis-ci.org/yrro/temper-exporter)

Running
-------

```
$ python3 -m pip install git+https://github.com/yrro/temper-exporter.git
$ temper-exporter
```

You can then visit <http://localhost:9203/> to view sensor readings;
for instance:

```
...
...
```

Supprted Devices
----------------

Packaging
---------

To produce a Debian package:

```
$ debian/rules clean
$ dpkg-buildpackage -b
```

The `prometheus-temper-exporter` package will be created in the parent directory.

Prometheus configuration
------------------------

Something like the following:

```yaml
scrape_configs:
 - job_name: temper
   static_configs:
     - targets:
        - 192.0.2.1:9203
```

Exporter Configuration
----------------------

Some useful options can be given to `exporter.py` on the command line.

```
$ temper-exporter
usage: temper-exporter [-h] [--bind-address BIND_ADDRESS] [--bind-port BIND_PORT]
                       [--bind-v6only {0,1}] [--thread-count THREAD_COUNT]

optional arguments:
  -h, --help            show this help message and exit
  --bind-address BIND_ADDRESS
                        IPv6 or IPv4 address to listen on
  --bind-port BIND_PORT
                        Port to listen on
  --bind-v6only {0,1}   If 1, prevent IPv6 sockets from accepting IPv4
                        connections; if 0, allow; if unspecified, use OS
                        default
  --thread-count THREAD_COUNT
                        Number of request-handling threads to spawn
```

Development
-----------

I'm trying to keep things simple and rely only on the Python standard library,
[pyudev](http://pypi.python.org/pypi/pyudev) and the
[prometheus_client](https://github.com/prometheus/client_python) module.

To run `exporter` from source:

```
$ python3 -m pip install -e .
$ temper-exporter
```

or, without installing:


```
$ python3 -m temper_exporter
```
