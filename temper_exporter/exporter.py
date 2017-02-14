import cgi
import html
import io
import socket
import urllib
import wsgiref.util

import prometheus_client

from . import temper

def wsgi_app(environ, start_response):
    '''
    Base WSGI application that routes requests to other applications.
    '''
    name = wsgiref.util.shift_path_info(environ)
    if name == '':
        return front(environ, start_response)
    elif name == 'metrics':
        return prometheus_app(environ, start_response)
    return not_found(environ, start_response)

def front(environ, start_response):
    '''
    Front page, linking to the metrics URL.
    '''
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [
        b'<html>'
            b'<head><title>TEMPer Exporter</title></head>'
            b'<body>'
                b'<h1>TEMPer Exporter</h1>'
                b'<p><a href="/metrics">Metrics</a></p>'
            b'</body>'
        b'</html>'
    ]

prometheus_app = prometheus_client.make_wsgi_app()

def not_found(environ, start_response):
    '''
    How did we get here?
    '''
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Not Found\r\n']
