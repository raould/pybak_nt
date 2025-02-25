#!/usr/bin/env python

import server
import service

PORT = 6969
BASE_DIR = '/Volumes/pybak'
BAK_SUBDIR = 'canonical'
HTML_SUBDIR = 'browse'
URLIZE = 'https://pybak.monad.com/'

def run():
    serverd = server.Server( BASE_DIR, BAK_SUBDIR, HTML_SUBDIR, URLIZE )
    httpd = service.make_service( PORT, serverd )
    print 'running...'
    httpd.serve_forever()
    print '...done'

if __name__ == '__main__':
    run()

