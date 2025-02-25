#!/usr/bin/env python

import sys
import os
import os.path
import metadata
import util
import traceback
import visit_core

def visit_single( file_count, full_path, data ):
    visit_core.log( "+ visit_single: checking %s\n" % full_path )
    UID = data[0]
    GID = data[1]
    dry_run = data[2]
    if util.smells_like_json_metadata( full_path ):
        visit_core.log( "1 visit_single: updating %s\n" % full_path )
        md = metadata.read_json_path( full_path )
        if md != None and not dry_run:
            visit_core.log( "2 visit_single: write %s\n" % full_path )
            metadata.write_json_path( md, full_path )
            visit_core.log( "3 visit_single: chown %s\n" % full_path )
            os.chown( full_path, UID, GID )
            file_count = file_count+1
        else:
            visit_core.log( "2 visit_single: skipping\n" )
    visit_core.log( "- visit_single\n" )

#----------------------------------------

def usage(msg=None):
    if msg:
        visit_core.log_error("[%s]\n" % msg)
    visit_core.log_error( "usage: %s {--dryrun} <dir> <chown-uid> <chown-gid>\n" % sys.argv[0] )
    sys.exit()

if __name__ == '__main__':
    # TODO: convert to using util.eat_arg().
    import sys
    if not sys.argv or len(sys.argv) < 4:
        usage()
    try:
        dm = visit_core.main_helper( usage )
        src = os.path.abspath( sys.argv[1] )
        uid = int(sys.argv[2])
        gid = int(sys.argv[3])
        f = visit_core.visit( src, dm['max_depth'], visit_single, None, (uid,gid,dm['dry_run']) )
    except:
        usage(msg="args: %s" % traceback.format_exception(*sys.exc_info()))
    print( "visited %s files." % f )
