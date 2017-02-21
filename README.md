temper-exporter
============

Exports readings from various PCsensor TEMPer devices for
[Prometheus](https://prometheus.io/).

[![Build Status](https://travis-ci.org/yrro/temper-exporter.svg?branch=master)](https://travis-ci.org/yrro/temper-exporter)

Acknowledgements and thanks to edorfaus's
[TEMPered](https://github.com/edorfaus/TEMPered) project for the information
about how to communicate with the supported devices.

Supported Devices
-----------------

 * `TEMPer2_M12_V1.3` - sold as "TEMPer2"; two temperature sensors, one on an
   external probe
 * `TEMPer1F_H1V1.5F` - sold as "TEMPerHUM": one temperature sensor and one
   humidity sensor

The Linux `hidraw` API is used to communicate with the devices.
Devices are identified by their corresponding USB interface's `modalias`
attribute.

Running
-------

```
$ python3 -m pip install git+https://github.com/yrro/temper-exporter.git
$ temper-exporter
```

You can then visit <http://localhost:9204/> to view sensor readings;
for instance:

```
# HELP temper_temperature_celsius Temperature reading
# TYPE temper_temperature_celsius gauge
temper_temperature_celsius{name="internal",phy="usb-3f980000.usb-1.4/input1",version="TEMPer2_M12_V1.3"} 21.625
temper_temperature_celsius{name="external",phy="usb-3f980000.usb-1.4/input1",version="TEMPer2_M12_V1.3"} 20.625
temper_temperature_celsius{name="",phy="usb-3f980000.usb-1.3/input1",version="TEMPer1F_H1V1.5F"} 25.980000000000004
# HELP temper_humidity_rh Relative humidity reading
# TYPE temper_humidity_rh gauge
temper_humidity_rh{name="",phy="usb-3f980000.usb-1.3/input1",version="TEMPer1F_H1V1.5F"} 57.18932593800001
```

The following labels are used:

 * `name`: optional label used on devices with more than one sensor
 * `phy`: physical location of the device (USB bus and ports through which it is
   attached)
 * `version`: string returned from the device in response to the 'get version'
   command.

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
        - 192.0.2.1:9204
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

To run the tests:

```
$ python3 -m pytest
```

To run `exporter` from source:

```
$ python3 -m pip install -e .
$ temper-exporter
```

or, without installing:


```
$ python3 -m temper_exporter
```

Don't forget to place the udev rules in place so that you have permission to
access the device nodes.
