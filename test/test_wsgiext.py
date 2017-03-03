import errno
import functools
import http.client
import socket
import socketserver
import threading
from unittest import mock
from urllib import error, request
from wsgiref import simple_server

import pytest

from temper_exporter import wsgiext

def app(status, environ, start_response):
    start_response(status, [('content-type', 'text/plain')])
    return [b'blah\r\n']

class EchoRequestHandler(socketserver.StreamRequestHandler):
    timeout = 1

    def handle(self):
        self.wfile.write(self.rfile.readline())

class TPServer(wsgiext.ThreadPoolServer, simple_server.WSGIServer):
    pass

def test_ThreadPoolServer():
    server = TPServer(('', 0), EchoRequestHandler)
    t = threading.Thread(target=functools.partial(server.serve_forever, poll_interval=0.1), daemon=True)
    t.start()
    with socket.socket() as s:
        s.connect(server.server_address)
        s.send(b'hello there\n')
        assert s.recv(1024) == b'hello there\n'
    server.shutdown()
    t.join()
    server.server_close()


def test_InstantShutdownServer():
    s = wsgiext.InstantShutdownServer(('', 0), socketserver.StreamRequestHandler)
    t = threading.Thread(target=functools.partial(s.serve_forever), daemon=True)
    t.start()
    s.send_stop()
    t.join()
    s.server_close()


@pytest.mark.parametrize('address, v6only, expected_family, expected_v6only', [
    ('0.0.0.0', None,  socket.AddressFamily.AF_INET, None),
    ('0.0.0.0',    0,  socket.AddressFamily.AF_INET, None),
    ('0.0.0.0',    1,  socket.AddressFamily.AF_INET, None),
    (     '::', None, socket.AddressFamily.AF_INET6, int(open('/proc/sys/net/ipv6/bindv6only').read())),
    (     '::',    0, socket.AddressFamily.AF_INET6, 0),
    (     '::',    1, socket.AddressFamily.AF_INET6, 1),
])
def test_IPv64Server(address, v6only, expected_family, expected_v6only):
    s = wsgiext.IPv64Server((address, 0), socketserver.StreamRequestHandler, bind_v6only=v6only)
    assert s.address_family == expected_family
    try:
        assert s.socket.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY) == expected_v6only
    except OSError as e:
        if e.errno == errno.ENOTSUP and expected_v6only is None:
            pass
        else:
            raise

@pytest.mark.parametrize('status, expected', [
    ('200 OK', True),
    ('500 Not OK', False),
])
def test_HealthCheckServer_health(status, expected):
    s = wsgiext.HealthCheckServer(('', 0), simple_server.WSGIRequestHandler)
    s.set_app(functools.partial(app, status))
    t = threading.Thread(target=functools.partial(s.serve_forever, poll_interval=0.1), daemon=True)
    t.start()
    assert s.healthy() == expected
    s.shutdown()
    t.join()
    s.server_close()

def test_HealthCheckServer_unhealthy_on_client_error(mocker):
    con = mock.create_autospec(http.client.HTTPConnection)
    con.request.side_effect = http.client.HTTPException
    mocker.patch('http.client.HTTPConnection', mock.create_autospec(http.client.HTTPConnection, return_value=con))

    s = wsgiext.HealthCheckServer(('', 0), simple_server.WSGIRequestHandler)
    s.set_app(functools.partial(app, '200 OK'))
    t = threading.Thread(target=functools.partial(s.serve_forever, poll_interval=0.1), daemon=True)
    t.start()
    assert not s.healthy()
    assert not con.getresponse.called # because con.request raised HTTPException
    s.shutdown()
    t.join()
    s.server_close()

class SRH(wsgiext.SilentRequestHandler):
    def log_date_time_string(self):
        return ':datetime:'

@pytest.mark.parametrize('status, expected', [
    ('200 OK', ''),
    ('400 Bad Request', '127.0.0.1 - - [:datetime:] "GET / HTTP/1.1" 400 6\n'),
], ids=['silent', 'not silent'])
def test_SilentRequestHandler(capsys, status, expected):
    s = simple_server.WSGIServer(('', 0), SRH)
    s.set_app(functools.partial(app, status))
    t = threading.Thread(target=functools.partial(s.serve_forever, poll_interval=0.1), daemon=True)
    t.start()

    try:
        with request.urlopen('http://{}:{}/'.format(*s.server_address)) as r:
            pass
    except error.HTTPError as e:
        pass

    s.shutdown()
    t.join()
    s.server_close()

    out, err = capsys.readouterr()
    assert err == expected
