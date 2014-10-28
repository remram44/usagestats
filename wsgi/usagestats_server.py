"""Simple WSGI script to store the usage reports.
"""


import os
import re


DESTINATION = b'.'  # Current directory
MAX_SIZE = 524288  # 512 KiB


date_format = re.compile(br'^[0-9]{2,12}\.[0-9]{3}$')


def store(report, address):
    """Stores the report on disk.
    """
    lines = [l for l in report.split(b'\n') if l]
    for line in lines:
        if line.startswith(b'date:'):
            date = line[5:]
            if date_format.match(date):
                filename = b'report_' + date + b'.txt'
                if os.path.exists(filename):
                    return "file exists"
                with open(os.path.join(DESTINATION, filename), 'wb') as fp:
                    if not isinstance(address, bytes):
                        address = address.encode('ascii')
                    fp.write(b'remote_addr:' + address + b'\n')
                    fp.write(report)
                return None
            else:
                return "invalid date"
    return "missing date field"


def application(environ, start_response):
    """WSGI interface.
    """

    # Gets the posted input
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        if request_body_size > MAX_SIZE:
            response_body = b"Report too big"
            start_response('403 Forbidden',
                           [('Content-Type', 'text/plain'),
                            ('Content-Length', '%d' % len(response_body))])
            return [response_body]
    except ValueError:
        request_body_size = MAX_SIZE
    request_body = environ['wsgi.input'].read(request_body_size)

    # Tries to store
    response_body = store(request_body, environ.get('REMOTE_ADDR'))
    if not response_body:
        status = '200 OK'
        response_body = "stored"
    else:
        status = '501 Server Error'

    if not isinstance(response_body, bytes):
        response_body = response_body.encode('utf-8')

    # Sends the response
    start_response(status, [('Content-Type', 'text/plain'),
                            ('Content-Length', '%d' % len(response_body))])
    return [response_body]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    httpd = make_server(
        '',
        8000,
        application)

    # Wait for a single request, serve it and quit.
    httpd.handle_request()
