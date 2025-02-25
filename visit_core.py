#!/usr/bin/env python

import sys
import os
import os.path
import pathlib2
import traceback
import util
import metadata

gLogger = None

def getGlobalLogger():
    import logging
    global gLogger
    if gLogger == None:
        gLogger = logging.getLogger("pybak-visit")
        assert not gLogger == None
        hdlr = logging.FileHandler("/tmp/pybak-visit.log"+str(util.get_now_seconds()))
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        gLogger.addHandler(hdlr)
        gLogger.setLevel(logging.INFO)
    return gLogger

def log_error( msg, stack=False ):
    m = str(msg)
    if stack:
        s = ">".join( util.extract_callers() )
        m = "(%s) ... %s" % ( s, msg )
        if msg.startswith("+"):
            m = "+" + m
        elif msg.startswith( "-" ):
            m = "-" + m
    sys.stderr.write( m )
    getGlobalLogger().error( m )

def callersArgsMsg(offset=1):
    import inspect
    caller = inspect.stack()[offset][0]
    return str(inspect.getargvalues(caller))+"\n"

def logVars( *args ):
    log( str(args)+"\n", caller=util.extract_callers()[-1] )

def log( msg=None, caller=None ):
    if msg == None:
        msg = callersArgsMsg(2)
    else:
        msg = str(msg)
    if caller == None:
        caller = util.extract_callers()[-1]
    m = "@%s(): %s" % ( caller, msg )
    if msg.startswith("+"):
        m = "+" + m
    elif msg.startswith( "-" ):
        m = "-" + m
    sys.stdout.write( m )
    getGlobalLogger().info( m )

def is_too_deep( max_depth, cur_depth ):
    return max_depth != None and cur_depth > max_depth

def is_cache_path( full_path ):
    # todo: Browser caches; Library on Mac OS X; etc. (but we'd need more context passed in?)
    cache_dir_names = set( x for x in [ ".git", ".hg", ".DS_Store" ] )
    parts = set( pathlib2.Path( full_path ).parts )
    i = cache_dir_names.intersection( parts )
    return len(i) > 0

def is_pybak_path( full_path ):
    return \
        util.smells_like_canonical( full_path ) or \
        util.smells_like_any_metadata( full_path ) or \
        util.smells_like_browse( full_path )

# 'data' is an euphamism for 'a sh*tty hack instead of *kwargs'!!! :-(
def visit( cur_dir, max_depth, visit_file, visit_pre_dir=None, data=None ):
    if not os.path.isdir( cur_dir ):
        raise Exception( "%s wasn't a directory!" % cur_dir )
    if visit_pre_dir != None:
        visit_pre_dir( cur_dir, max_depth, 0, data )
    return _visit( cur_dir, max_depth, 0, visit_file, visit_pre_dir, 0, data )

def _visit( cur_dir, max_depth, cur_depth, visit_file, visit_pre_dir, file_count, data=None ):
    if is_too_deep( max_depth, cur_depth ):
        return file_count
    dirs = []
    try:
        files = os.listdir( cur_dir )
    except:
        log( "ERROR\t%s" % sys.exc_info()[0] )
        return 0
    for f in files:
        full_path = os.path.join( cur_dir, f )
        if os.path.isfile( full_path ):
            file_count += 1
            visit_file( file_count, full_path, data )
        elif os.path.isdir( full_path ):
            dirs.append( full_path )
    # let us blow the stack, why don't we.
    for d in dirs:
        if visit_pre_dir != None:
            visit_pre_dir( d, max_depth, cur_depth+1, data )
        file_count = _visit( d, max_depth, cur_depth+1, visit_file, visit_pre_dir, file_count, data )
    return file_count

def main_helper( usage, support_dryrun=True, support_maxdepth=True, support_maxbytes=True, support_debug=True ):
    eaten = {}
    try:
        if util.eat_arg(sys.argv, "help", nodash=True, remove=True):
            usage(msg="help")
            return eaten
        if support_dryrun:
            dry_runA = util.eat_arg(sys.argv, "dryrun", remove=True)
            dry_runB = util.eat_arg(sys.argv, "dry-run", remove=True)
            eaten['dry_run'] = dry_runA or dry_runB
        if support_maxdepth:
            max_depth = util.eat_arg(sys.argv, "maxdepth", remove=True, reqval=True)
            eaten['max_depth'] = int(max_depth) if max_depth else None
        if support_maxbytes:
            max_bytes = util.eat_arg(sys.argv, "maxbytes", remove=True, reqval=True)
            eaten['max_bytes'] = int(max_bytes) if max_bytes else None
        if support_debug:
            debug = util.eat_arg(sys.argv, "debug", remove=True)
            eaten['debug'] = (debug != None)
        sys.stdout.write( "found args: %s\n" % eaten )
        sys.stdout.write( "arg leftovers: %s\n" % sys.argv )
        return eaten
    except:
        usage(msg=(sys.exc_info()[0]))
