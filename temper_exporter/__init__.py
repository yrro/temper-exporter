import argparse
import ipaddress
import functools
import http.client
import os
import pyudev
import signal
import sys
import threading
import wsgiref.simple_server

import prometheus_client
import prometheus_client.core as core

from . import exporter
from . import temper
from . import wsgiext

def main():
    '''
    You are here.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind-address', type=ipaddress.ip_address, default='::', help='IPv6 or IPv4 address to listen on')
    parser.add_argument('--bind-port', type=int, default=9204, help='Port to listen on')
    parser.add_argument('--bind-v6only', type=int, choices=[0, 1], help='If 1, prevent IPv6 sockets from accepting IPv4 connections; if 0, allow; if unspecified, use OS default')
    parser.add_argument('--thread-count', type=int, help='Number of request-handling threads to spawn')
    args = parser.parse_args()

    collector = exporter.Collector()
    core.REGISTRY.register(collector)

    server = wsgiext.Server((args.bind_address, args.bind_port), wsgiext.SilentRequestHandler, args.thread_count, args.bind_v6only)
    server.set_app(prometheus_client.make_wsgi_app())
    wsgi_thread = threading.Thread(target=functools.partial(server.serve_forever, poll_interval=86400), name='wsgi')

    ctx = pyudev.Context()
    mon = temper.monitor(ctx)
    observer_thread = pyudev.MonitorObserver(mon, name='monitor', callback=collector.handle_device_event)

    health_thread = Health(collector, server)

    def handle_sigterm(signum, frame):
        health_thread.send_stop()
        server.shutdown()
        observer_thread.send_stop()
    signal.signal(signal.SIGTERM, handle_sigterm)

    wsgi_thread.start()
    observer_thread.start()
    health_thread.start()

    collector.coldplug_scan(ctx)

    wsgi_thread.join()
    observer_thread.join()
    health_thread.join()

    server.server_close()

    sys.exit(health_thread.exit_status)

class Health(threading.Thread):
    def __init__(self, collector, server, interval=30, *args, **kwargs):
        super().__init__(name='health', *args, **kwargs)
        self.__collector = collector
        self.__server = server
        self.__interval = interval
        self.__event = threading.Event()
        self.exit_status = 0

    def send_stop(self):
        '''
        Cause the thread to exit.
        '''
        self.__event.set()

    def run(self):
        '''
        Monitor the health of the service.

        If something fails, sends SIGTERM to the process. The signal handler
        (which always runs in the main thread) will shut down the components
        and then the process will exit.

        We don't have to provide detailed error messages, since the component
        that failed should already have logged something useful.
        '''
        try:
            addr, port, *rest = self.__server.socket.getsockname()
            while not self.__event.wait(self.__interval):
                # Collector checks
                if self.__collector.exceptions._value.get() > 0:
                    self.exit_status = 1
                    break
                elif self.__collector.errors._value.get() > 0:
                    self.exit_status = 1
                    break
                # WSGIServer checks
                c = http.client.HTTPConnection(addr, port, timeout=5)
                try:
                    c.request('GET', '/')
                except http.client.HTTPException:
                    self.exit_status = 1
                    break
                r = c.getresponse()
                if r.status != 200:
                    self.exit_status = 1
                    break
        except:
            self.exit_status = 1
            raise
        finally:
            if self.exit_status != 0:
                os.kill(os.getpid(), signal.SIGTERM)
