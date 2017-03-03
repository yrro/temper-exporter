import concurrent.futures
from contextlib import suppress
import http
import http.client
import ipaddress
import socket
import socketserver
import sys
import wsgiref.simple_server

class ThreadPoolServer(socketserver.TCPServer):
    def __init__(self, *args, max_threads=None, **kwargs):
        if sys.version_info.major <= 3 and sys.version_info.minor < 5:
            if max_threads is None:
                max_threads = 4
        self.__ex = concurrent.futures.ThreadPoolExecutor(max_threads)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        self.__ex.submit(self.__process_request_thread, request, client_address)

    def __process_request_thread(self, request, client_address):
        '''
        Taken from socketserver.ThreadingMixIn
        '''
        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except Exception:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def server_close(self):
        super().server_close()
        self.__ex.shutdown()

class InstantShutdownServer(socketserver.TCPServer):
    '''
    Connecting to the underlying SocketServer's listening socket will wake it
    up. It will then immediately check the shutdown flag, rather than waiting
    for the poll_interval.
    '''
    def send_stop(self):
        # Unfortunately there is no public API for setting this flag, and
        # calling super().shutdown() here would block us
        self._BaseServer__shutdown_request = True
        # Now connect to the server to cause it to wake up
        with socket.socket(self.socket.family) as s:
            s.setblocking(0)
            with suppress(BlockingIOError):
                s.connect(self.socket.getsockname())

class IPv64Server(socketserver.TCPServer):
    def __init__(self, server_address, *args, bind_v6only, **kwargs):
        ip = ipaddress.ip_address(server_address[0])
        self.address_family = socket.AF_INET6 if ip.version == 6 else socket.AF_INET
        self.__bind_v6only = bind_v6only
        super().__init__(server_address, *args, **kwargs)

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IP, 15, 1) # IP_FREEBIND
        if self.__bind_v6only is not None and self.address_family == socket.AF_INET6:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, self.__bind_v6only)
        super().server_bind()

class HealthCheckServer(wsgiref.simple_server.WSGIServer):
    def healthy(self):
        c = http.client.HTTPConnection(self.server_address[0], self.server_address[1], timeout=5)
        try:
            c.request('GET', '/')
        except http.client.HTTPException:
            return False
        with c.getresponse() as r:
            if r.status != http.HTTPStatus.OK:
                return False
        return True

class SilentRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    def log_request(self, code='-', message='-'):
        if isinstance(code, str) and code[0] < '4':
            # WSGIRequestHandler always calls this with a string.
            return
        elif isinstance(code, http.HTTPStatus) and code.value < 400:
            # But a bad request is handled by BaseHTTPRequestHandler, which
            # uses an HTTPStatus
            return
        super().log_request(code, message)

class Server(HealthCheckServer, IPv64Server, InstantShutdownServer, ThreadPoolServer, wsgiref.simple_server.WSGIServer):
    def __init__(self, server_address, **kwargs):
        super().__init__(server_address, SilentRequestHandler, **kwargs)
