#!/usr/bin/env python

import re
import traceback
import util
import os
import os.path
import sys
import shutil
import visit_core

def copy2( src_path, dst_path, src_sum=None ):
    dst_sum = util.calculate_checksum( dst_path )
    if not dst_sum:
        visit_core.log( "new %s -> %s\n" % ( src_path, dst_path ) )
        shutil.copy2( src_path, dst_path )
    else:
        if not src_sum:
            src_sum = util.calculate_checksum( src_path )
        if src_sum == dst_sum:
            visit_core.log( "%s == %s\n" % ( src_path, dst_path ) )
        else:
            dst_path_other = dst_path + "." + dst_sum
            visit_core.log( "%s -> %s\n" % ( src_path, dst_path_other ) )
            copy2( src_path, dst_path_other, src_sum ) # avoid copying file if it is already there.

def should_copy( src_path, exclude_regexp ):
    should = True
    if exclude_regexp:
        match = re.match( exclude_regexp, src_path )
        should = False if match else True
    return should

def visit_single( file_count, src_path, data ):
    if should_copy( src_path, data['exclude_regexp'] ):
        dst_path = os.path.join( data['dst'], os.path.basename( src_path ) )
        copy2( src_path, dst_path )
    else:
        visit_core.log( "excluding %s\n" % src_path )
    
def usage(msg=None):
    if msg:
        visit_core.log_error("[%s]\n" % msg)
    visit_core.log_error( "ERROR:\n" )
    visit_core.log_error( " usage: %s {--dryrun} {--maxdepth N} {--exclude_regexp 'regexp'} <dst dir> <[src1,src2,src3,...]>\n" % sys.argv[0] )
    visit_core.log_error( " was: %s\n" % " ".join( sys.argv ) )
    sys.exit()

if __name__ == '__main__':
    dm = visit_core.main_helper( usage )
    dry_run = True if dm['dry_run'] else False
    exclude_regexp = util.eat_arg(sys.argv, "exclude_regexp", remove=True, reqval=True)
    try:
        dst = sys.argv[1]
        srcs = sys.argv[2:]
    except:
        sys.stderr.write( "usage exception: %s\n" % traceback.format_exception( *sys.exc_info() ) )
        usage(msg=(sys.exc_info()[0]))

    print sys.argv
    for a in sys.argv:
        if a[0] == "-" or a[0] == "--":
            usage( "unknown flag: %s" % a )
    try:
        count = 0
        for src in srcs:
            count += visit_core.visit( src,
                                       dm['max_depth'],
                                       visit_single,
                                       {'dry_run':dry_run,
                                        'dst':os.path.abspath(dst),
                                        'srcs':map(lambda d:os.path.abspath(d), srcs),
                                        'exclude_regexp':exclude_regexp} )
        visit_core.log( "visited %s file(s)\n" % count )
    except:
        visit_core.log_error( "ERROR: %s\n" % traceback.format_exception( *sys.exc_info() ) )
