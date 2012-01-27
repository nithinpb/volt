"""HTTP server for Volt's static output.

This module is just a simple wrapper for SimpleHTTPServer with more compact
log message and the option to set directory to serve. By default, it searches
for the "site" directory and serves the contents.
"""

import argparse
import os
import posixpath
import sys
import urllib
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from socket import error

from volt import __version__
from volt.util import is_valid_root, write, inform, notify, warn


class VoltHTTPRequestHandler(SimpleHTTPRequestHandler):

    server_version = 'VoltHTTPServer/' + __version__

    def log_error(self, format, *args):
        """Logs the error.

        Overwritten to unclutter log message.
        """
        pass

    def log_message(self, format, *args):
        """Prints the log message.

        Overrides parent log_message to provide a more compact output.

        """
        message = "[%s] %s\n" % (self.log_date_time_string(), format % args)

        if int(args[1]) >= 400:
            warn(message)
        elif int(args[1]) >= 300:
            inform(message)
        else:
            write(message)


    def log_request(self, code='-', size='-'):
        """Logs the accepted request.

        Overrides parent log_request so 'size' can be set dynamically.

        """
        ### HACK, add code for 404 processing later
        if code <= 200:
            actual_file = os.path.join(self.file_path, 'index.html')
            if os.path.isdir(self.file_path):
                if os.path.exists(actual_file) or \
                   os.path.exists(actual_file[:-1]):
                    size = os.path.getsize(actual_file)
            else:
                size = os.path.getsize(self.file_path)
        self.log_message('"%s" %s %s',
                         self.requestline, str(code), str(size))

    def translate_path(self, path):
        """Returns filesystem path of from requests.

        Overrides parent translate_path to enable custom directory setting.
        """
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        # set file path as attribute, to get size in log_request()
        self.file_path = path
        return self.file_path

def run(options):
    """Runs the server.

    Arguments:
    options: Namespace object from argparse.ArgumentParser()
    """
    options.volt_dir = os.path.abspath(options.volt_dir)
    address = ('127.0.0.1', options.server_port)
    try:
        os.chdir(os.path.join(options.volt_dir, 'site'))
        server = HTTPServer(address, VoltHTTPRequestHandler)
    except Exception, e:
        ERRORS = {
            2: "Directory 'site' not found in %s" % options.volt_dir,
            13: "You don't have permission to access port %s" % 
                (options.server_port),
            98: "Port %s already in use" % (options.server_port),
        }
        try:
            error_message = ERRORS[e.args[0]]
        except (AttributeError, KeyError):
            error_message = str(e)
        warn("Error: %s\n" % error_message)
        sys.exit(1)

    run_address, run_port = server.socket.getsockname()
    if run_address == '127.0.0.1':
        run_address = 'localhost'
    notify("\nVolt %s Development Server\n" % __version__)
    write("Serving %s/\n" 
          "Running at http://%s:%s/\n"
          "CTRL-C to stop.\n\n" % 
          (options.volt_dir, run_address, run_port)
         )

    try:
        server.serve_forever()
    except:
        server.shutdown()
        notify("\nServer stopped.\n\n")
        sys.exit(0)

    options.func(options)
