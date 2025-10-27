#!/usr/bin/env python

import sys
import service
import server
import util
import datetime

gTest = False

def getPREFIX():
    if gTest:
        return '/tmp/pybak'
    else:
        return ''
def getURLIZE():
    if gTest:
        return 'file://localhost/tmp/mnt/pybak'
    else:
        return 'http://www.psync-o-pathics.com'
def getPORT():
    if gTest:
        return 1234
    else:
        return 6969
def getLOG_FILE(): return '%s/var/log/pybakd.log' % getPREFIX()
def getPID_FILE(): return '%s/var/run/pybakd/pybakd.pid' % getPREFIX()
def getBASE_DIR(): return '%s/home/pybak' % getPREFIX()
def getBAK_SUBDIR(): return 'canonical'

def user_prog():
    print( "pybakd: run..." )
    util.ensure_path( getBASE_DIR() )
    sys.stdout.write( "%s %s\n" % ( getBASE_DIR(), getBAK_SUBDIR() ) )
    serverd = server.Server( getBASE_DIR(), getBAK_SUBDIR() )
    httpd = service.make_service( getPORT(), serverd )
    httpd.serve_forever()

# see http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012
import sys, os

class Log:
    """file like for writes with auto flush after each write
    to ensure that everything is logged, even during an
    unexpected exit."""
    def __init__(self, f):
        self.f = f
    def write(self, s):
        self.f.write(s)
        self.f.flush()
        os.fdatasync(self.f)

def main_daemon_loop( p ):
    #redirect outputs to a logfile
    log_file = getLOG_FILE()
    sys.stdout.write( "%s %s %s\n" % ( getBASE_DIR(), getBAK_SUBDIR(), log_file ) )
    util.ensure_parent_path( log_file )
    sys.stdout = sys.stderr = Log(open(log_file, 'a+'))

    #ensure the that the daemon runs a normal user
    os.setegid(0)     #set group "root"
    os.seteuid(0)     #set user "root"

    #start the user program here:
    print( "pybakd: starting core program" )
    p()

def is_parent_pid( pid ):
    return pid > 0

def is_child_pid( pid ):
    return not is_parent_pid( pid )

def main_daemon( p ):
    # do the UNIX double-fork magic, see Stevens' "Advanced
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try:
        pid = os.fork()
        if is_parent_pid( pid ):
            # exit first parent
            sys.exit( 0 )
        else:
            print( "pybakd: child 1 forked" )
    except OSError, e:
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit( 1 )

    # decouple from parent environment
    os.chdir( "/" )   #don't prevent unmounting....
    os.setsid()
    os.umask( 0 )

    # do second fork
    try:
        pid = os.fork()
        if is_parent_pid( pid ):
            # exit from second parent, print eventual PID before
            #print "Daemon PID %d" % pid
            util.ensure_parent_path( getPID_FILE() )
            open( getPID_FILE(),'w' ).write( "%d"%pid )
            sys.exit( 0 )
        else:
            print( "pybakd: child 2 forked" )
    except OSError, e:
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit( 1 )

    # start the daemon main loop
    print( "pybakd: starting daemon loop..." )
    main_daemon_loop( p )

if __name__ == "__main__":
    print( "pybakd: started with %s" % sys.argv )
    if '-test' in sys.argv or '--test' in sys.argv:
        gTest = True
        user_prog()
    elif '-docker' in sys.argv:
        user_prog()
    else:
        main_daemon( user_prog )
