#!/usr/bin/env python

# note that the http codes are not really used entirely properly. just sorta close enough.

import sys
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import server
import util
import binascii
import json

def log_error( msg ):
    sys.stderr.write( msg )

def log( msg ):
    sys.stdout.write( msg )

class RequestHandler( BaseHTTPRequestHandler ):

    def do_POST( self ):
        log("[-> service] do_POST %s\n" % self.path )
        import urllib
        if( self.path == "/save-chunk" ):
            self.save_chunk()
        elif( self.path == "/save-md" ):
            self.save_md()
        elif( self.path == "/match-list" ):
            self.match_list()
        elif( self.path == "/get-length" ):
            self.get_length()
        else:
            self.send_response( 400 )

    def get_x_headers( self ):
        jxh = self.headers.getheader( 'x-headers' )
        if jxh == None:
            raise IOError( "missing required x-headers, saw only %s" % self.headers )
        return json.loads(jxh)

    def parse_file_request( self ):
        import inspect
        log( "[->service] <in %s> parse_file_request(): headers = %s\n" % ( inspect.stack()[1][3], self.headers ) )
        x_headers = self.get_x_headers()
        x_headers['x-chunk-length'] = int( self.headers.getheader( 'content-length' ) )
        # encoding can be None, means raw bytes.
        if x_headers['x-chunk-length']==None or \
                x_headers['x-offset']==None or \
                x_headers['x-hostname']==None or \
                x_headers['x-py-platform-system'] == None or \
                x_headers['x-py-platform-uname'] == None or \
                x_headers['x-py-sys-byteorder'] == None or \
                x_headers['x-py-os-path-sep'] == None or \
                x_headers['x-hexl-filepath']==None or \
                x_headers['x-hexl-filepath-parts']==None or \
                x_headers['x-checksum']==None or \
                x_headers['x-length']==None or \
                x_headers['x-is-canonical']==None or \
                x_headers['x-is-metadata']==None or \
                x_headers['x-isexe']==None or \
                x_headers['x-oldest']==None:
            # f2c, f2l are optional.
            raise IOError( "missing required header(s), saw only %s" % x_headers )
        log( "[->service] parse_file_request(): %s\n" % x_headers )
        return x_headers

    def save_md( self ):
        log( "[->service] save_md\n" )
        try:
            x_headers = self.parse_file_request()
            success = RequestHandler.server.save_md( x_headers, self.rfile, int(self.headers.getheader('content-length')) )
            if success:
                log( "[<-service] 200\n" )
                self.send_response( 200 )
            else:
                log( "[<-service] 409\n" )
                self.send_response( 409 )
        except IOError, ioe:
            log_error( "[<-service] error: %s\n" % ioe )
            self.send_response( 500 )

    def save_chunk( self ):
        log( "[->service] save_chunk\n" )
        try:
            x_headers = self.parse_file_request()
            success = RequestHandler.server.save_chunk( x_headers, self.rfile )
            if success:
                log( "[<-service] 200\n" )
                self.send_response( 200 )
            else:
                log( "[<-service] 409\n" )
                self.send_response( 409 )
        except util.AlreadyCompleted, aeae:
            log( "[<-service] 200 (AlreadyCompleted)\n" )
            self.send_response( 200 )
        except IOError, ioe:
            log_error( "[<-service] error: %s\n" % ioe )
            self.send_response( 500 )

    def match_list( self ):
        log( "[->service] match_list\n" )
        try:
            x_headers = self.get_x_headers()
            print x_headers
            json_response = RequestHandler.server.match_list( x_headers, self.rfile, int(self.headers.getheader('content-length')) )
            log( "[<-service] match_list: %s\n" % json_response )
            if len(json_response) > 0:
                self.send_response( 200 )
                self.send_header( "Content-type", "text/json" )
                self.end_headers()
                self.wfile.write( json_response )
                self.wfile.close()
            else:
                log_error( "[<-service] failed to build json_response\n" )
                self.send_response( 500 )
        except IOError, ioe:
            log_error( "[<-service] IOError: %s\n" % ioe )
            self.send_response( 500 )

    def get_length( self ):
        try:
            x_headers = self.parse_file_request()
            length = RequestHandler.server.get_length( x_headers )
            log( "[<-service] %s -> length = %s\n" %
                 (binascii.unhexlify(x_headers['x-hexl-filepath']),
                  length)
            )
            self.send_response( 200 )
            self.send_header( 'x-length', length )
            self.end_headers()
        except IOError, ioe:
            log_error( "[<-service] IOError: %s\n" % ioe )
            self.send_response( 500 )

def make_service( port, server ): # production entry point.
    print 'make_service: %s %s' % ( server, port )
    RequestHandler.server = server
    return HTTPServer( ('', port), RequestHandler )

def main(): # just for testing.
    try:
        util.require_args_or_die( ['base_dir', 'bak_subdir'] )
        pserver = server.Server( sys.argv[1], sys.argv[2] )
        port = 8080
        service = make_service( port, pserver )
        print 'Running...'
        service.serve_forever()
        print '...done.'
    except KeyboardInterrupt:
        service.socket.close()
        
if __name__ == '__main__':
    main()
