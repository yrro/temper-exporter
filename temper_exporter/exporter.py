import sys
import threading

import prometheus_client
import prometheus_client.core as core

class Collector:

    def __init__(self):
        self.__sensors = {}
        self.__read_lock = threading.Lock()
        self.__write_lock = threading.Lock()
        self.__healthy = True


    def collect(self):
        temp = core.GaugeMetricFamily('temper_temperature_celsius', 'Temperature reading', labels=['name', 'phy', 'version'])
        humid = core.GaugeMetricFamily('temper_humidity_rh', 'Relative humidity reading', labels=['name', 'phy', 'version'])

        # Prevent two threads from reading from a device at the same time.
        # Heavy handed, but easier than a lock for each device.
        with self.__read_lock:
            # Copy the dict so we can modify it during iteration
            for device, t in self.__sensors.copy().items():
                try:
                    readings = t.read_sensor()
                except IOError:
                    print('Error reading from {}'.format(device), file=sys.stderr)
                    self.__healthy = False
                    try:
                        t.close()
                    except IOError:
                        pass
                    with self.__write_lock:
                        del self.__sensors[device]
                    continue

                for type_, name, value in readings:
                    if type_ == 'temp':
                        temp.add_metric([name, t.phy(), t.version], value)
                    elif type_ == 'humid':
                        humid.add_metric([name, t.phy(), t.version], value)
                    else:
                        print('Unknown sensor type <{}>'.format(type_), file=sys.stderr)

        yield temp
        yield humid


    def coldplug_scan(self, devices):
        '''
        Call this from the main thread, after the device-event handling thread
        has started. That way, there's no chance of missed events between the
        time of the coldplug scan and the time that the netlink socket starts
        receiving events.
        '''
        for device in devices:
            self.handle_device_event(device)


    def handle_device_event(self, device):
        if device.action == 'add' or device.action is None:
            # If device.action is None then this is a coldplug event, which
            # can be handled as normal, since if a hotplug event for the
            # device already occurred then an entry for it will already be
            # in __sensors.
            self.__handle_device_add(device)
        elif device.action == 'remove':
            self.__handle_device_remove(device)


    def __handle_device_add(self, device):
        t = self.__sensors.get(device)
        if t is not None:
            return

        cls = self.class_for_device(device)
        if cls is None:
            return

        try:
            t = cls(device)
        except IOError:
            print('Error reading from {}'.format(device), file=sys.stderr)
            self.__healthy = False
            return

        with self.__write_lock:
            self.__sensors[device] = t


    def __handle_device_remove(self, device):
        with self.__write_lock:
            t = self.__sensors.pop(device, None)
        if t is not None:
            t.close()


    def class_for_device(self, device):
        '''
        Override this method. Given a pyudev.Device, it should return a
        temper.usb_temper class (not instance!) to handle the device.
        '''
        raise NotImplementedError

    def healthy(self):
        return self.__healthy
