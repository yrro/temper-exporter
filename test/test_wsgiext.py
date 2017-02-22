import errno
import functools
import socket
import socketserver
import threading
from urllib import error, request
from wsgiref import simple_server

import pytest

from temper_exporter import wsgiext

def app(status, environ, start_response):
    start_response(status, [('content-type', 'text/plain')])
    return [b'blah\r\n']


class TPServer(wsgiext.ThreadPoolServer, simple_server.WSGIServer):
    def __init__(self):
        self._ThreadPoolServer__pre_init(4)
        super().__init__(('', 0), simple_server.WSGIRequestHandler)

def test_ThreadPoolServer():
    s = TPServer()
    s.set_app(functools.partial(app, '200 OK'))
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    with request.urlopen('http://{}:{}/'.format(*s.server_address)) as r:
        assert r.read() == b'blah\r\n'
    s.shutdown()
    t.join()
    s.server_close()


def test_InstantShutdownServer():
    s = wsgiext.InstantShutdownServer(('', 0), socketserver.StreamRequestHandler)
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    s.send_stop()
    t.join()
    s.server_close()


class IServer(wsgiext.IPv64Server):
    def __init__(self, server_address, bind_v6only):
        self._IPv64Server__pre_init(server_address, bind_v6only)
        super().__init__(server_address, socketserver.StreamRequestHandler)

@pytest.mark.parametrize('address, v6only, expected_family, expected_v6only', [
    ('0.0.0.0', None,  socket.AddressFamily.AF_INET, None),
    ('0.0.0.0',    0,  socket.AddressFamily.AF_INET, None),
    ('0.0.0.0',    1,  socket.AddressFamily.AF_INET, None),
    (     '::', None, socket.AddressFamily.AF_INET6, int(open('/proc/sys/net/ipv6/bindv6only').read())),
    (     '::',    0, socket.AddressFamily.AF_INET6, 0),
    (     '::',    1, socket.AddressFamily.AF_INET6, 1),
])
def test_IPv64Server(address, v6only, expected_family, expected_v6only):
    s = IServer((address, 0), bind_v6only=v6only)
    assert s.address_family == expected_family
    try:
        assert s.socket.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY) == expected_v6only
    except OSError as e:
        if e.errno == errno.ENOTSUP and expected_v6only is None:
            pass
        else:
            raise

def test_HealthCheckServer_200():
    s = wsgiext.HealthCheckServer(('', 0), simple_server.WSGIRequestHandler)
    s.set_app(functools.partial(app, '200 OK'))
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    assert s.healthy()
    s.shutdown()
    t.join()
    s.server_close()

def test_HealthCheckServer_500():
    s = wsgiext.HealthCheckServer(('', 0), simple_server.WSGIRequestHandler)
    s.set_app(functools.partial(app, '500 Not OK'))
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    assert not s.healthy()
    s.shutdown()
    t.join()
    s.server_close()


class SRH(wsgiext.SilentRequestHandler):
    def log_date_time_string(self):
        return ':datetime:'

def test_SilentRequestHandler_200(capsys):
    s = simple_server.WSGIServer(('', 0), SRH)
    s.set_app(functools.partial(app, '200 OK'))
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    with request.urlopen('http://{}:{}/'.format(*s.server_address)) as r:
        pass
    s.shutdown()
    t.join()
    s.server_close()
    out, err = capsys.readouterr()
    assert err == ''

def test_SilentRequestHandler_400(capsys):
    s = simple_server.WSGIServer(('', 0), SRH)
    s.set_app(functools.partial(app, '400 Bad Request'))
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    try:
        with request.urlopen('http://{}:{}/'.format(*s.server_address)) as r:
            pass
    except error.HTTPError:
        pass
    s.shutdown()
    t.join()
    s.server_close()
    out, err = capsys.readouterr()
    assert err == '127.0.0.1 - - [:datetime:] "GET / HTTP/1.1" 400 6\n'
