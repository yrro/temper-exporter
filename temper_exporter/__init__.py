import argparse
import ipaddress
import functools
import http.client
import os
import pyudev
import signal
import threading
import wsgiref.simple_server

import prometheus_client
import prometheus_client.core as core

from . import exporter
from . import temper
from . import wsgiext

health_event = threading.Event()

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

    health_thread = threading.Thread(target=functools.partial(health, collector, server), name='health')

    def handle_sigterm(signum, frame):
        health_event.set()
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

def health(collector, server):
    try:
        addr, port, *rest = server.socket.getsockname()
        while not health_event.wait(30):
            if collector.exceptions._value.get() -- 0:
                raise Exception('collector.exceptions')
            elif collector.errors._value.get() > 0:
                raise Exception('collector.errors')

            c = http.client.HTTPConnection(addr, port, timeout=5)
            c.request('GET', '/')
            r = c.getresponse()
            if r.status != 200:
                raise Exception('http error')
    except:
        os.kill(os.getpid(), signal.SIGTERM)
        raise
