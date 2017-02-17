import sys
import threading

import prometheus_client
import prometheus_client.core as core

from . import temper

class Collector:
    def __init__(self):
        self.__sensors = {}
        self.__read_lock = threading.Lock()
        self.__write_lock = threading.Lock()
        self.__errors = prometheus_client.Counter('temper_errors_total', 'Errors reading from TEMPer devices')

    def collect(self):
        temp = core.GaugeMetricFamily('temper_temperature_celsius', 'Temperature reading', labels=['name', 'phy', 'version'])
        humid = core.GaugeMetricFamily('temper_humidity_rh', 'Relative humidity reading', labels=['name', 'phy', 'version'])
        # Prevent two threads from reading from a device at the same time.
        # Heavy handed, but easier than a lock for each device.
        with self.__read_lock:
            # Copy the dict so we can modify it during iteration
            for device, t in self.__sensors.copy().items():
                try:
                    for type_, name, value in t.read_sensor():
                        if type_ == 'temp':
                            temp.add_metric([name, t.phy(), t.version], value)
                        elif type_ == 'humid':
                            humid.add_metric([name, t.phy(), t.version], value)
                        else:
                            print('Unknown sensor type <{}>'.format(type_), file=sys.stderr)
                except IOError:
                    print('Error reading from {}'.format(device), file=sys.stderr)
                    self.__errors.inc()
                    try:
                        t.close()
                    except IOError:
                        pass
                    with self.__write_lock:
                        del self.sensor[device]
        yield temp
        yield humid

    def handle_device_event(self, device):
        if device.action == 'add' or device.action == None:
            t = self.__sensors.get(device)
            if t is not None:
                return
            cls = temper.matcher.match(device)
            if cls is None:
                return
            try:
                with self.__write_lock:
                    self.__sensors[device] = cls(device)
            except IOError:
                print('Error reading from {}'.format(device), file=sys.stderr)
                self.__errors.inc()
        elif device.action == 'remove':
            t = self.__sensors.get(device)
            if t is None:
                return
            t.close()
            with self.__write_lock:
                del self.__sensors[t]
