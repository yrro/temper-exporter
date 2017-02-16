import argparse
import ipaddress
import functools
import pyudev
import signal
import sys
import threading
import wsgiref.simple_server

import prometheus_client
import prometheus_client.core as core

from . import temper
from . import wsgiext

def main():
    '''
    You are here.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind-address', type=ipaddress.ip_address, default='::', help='IPv6 or IPv4 address to listen on')
    parser.add_argument('--bind-port', type=int, default=9203, help='Port to listen on')
    parser.add_argument('--bind-v6only', type=int, choices=[0, 1], help='If 1, prevent IPv6 sockets from accepting IPv4 connections; if 0, allow; if unspecified, use OS default')
    parser.add_argument('--thread-count', type=int, help='Number of request-handling threads to spawn')
    args = parser.parse_args()

    collector = Collector()
    core.REGISTRY.register(collector)

    server = wsgiext.Server((args.bind_address, args.bind_port), wsgiref.simple_server.WSGIRequestHandler, args.thread_count, args.bind_v6only)
    server.set_app(prometheus_client.make_wsgi_app())
    wsgi_thread = threading.Thread(target=functools.partial(server.serve_forever, poll_interval=5), name='wsgi', daemon=True)
    wsgi_thread.start()

    ctx = pyudev.Context()
    mon = temper.monitor(ctx)
    observer_thread = pyudev.MonitorObserver(mon, name='monitor', callback=functools.partial(handle_device_event, collector))
    observer_thread.start()

    for device in temper.list_devices(ctx):
        # It's OK to call this from the main thread because it takes the lock
        # on the sensor list
        handle_device_event(collector, device)

    def handle_sigterm(signum, frame):
        server.shutdown()
        observer_thread.send_stop()
    signal.signal(signal.SIGTERM, handle_sigterm)

    wsgi_thread.join()
    observer_thread.join()

def handle_device_event(collector, device):
    with collector.write_lock:
        if device.action == 'add' or device.action == None:
            t = collector.sensors.get(device)
            if t is not None:
                return
            cls = temper.matcher.match(device)
            if cls is None:
                return
            try:
                collector.sensors[device] = cls(device)
            except IOError:
                print('Error reading from {}'.format(device), file=sys.stderr)
        elif device.action == 'remove':
            t = collector.sensors.get(device)
            if t is None:
                return
            t.close()
            del collector.sensors[t]

class Collector:
    def __init__(self):
        self.sensors = {}
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()

    def collect(self):
        temp = core.GaugeMetricFamily('temper_temperature_celsius', 'Temperature reading', labels=['name', 'phy', 'version'])
        humid = core.GaugeMetricFamily('temper_humidity_rh', 'Temperature reading', labels=['name', 'phy', 'version'])
        # Prevent two threads from reading from a device at the same time.
        # Heavy handed, but easier than a lock for each device.
        with self.read_lock:
            # Copy the dict so we can modify it during iteration
            for device, t in self.sensors.copy().items():
                try:
                    for type_, name, value in t.read_sensor():
                        if type_ == 'temp':
                            temp.add_metric([name, t.phy(), t.version], value)
                        elif type_ == 'humid':
                            humid.add_metric([name, t.phy(), t.version], value)
                        else:
                            print('Unknown sensor type <{}>'.format(type_), file=sys.stderr)
                except IOError:
                    try:
                        t.close()
                    except IOError:
                        print('Error reading from {}'.format(device), file=sys.stderr)
                    with self.write_lock:
                        del self.sensor[device]
        yield temp
        yield humid
