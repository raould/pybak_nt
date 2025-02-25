#!/usr/bin/env python
import os
import os.path
import shutil
import util
import visit_core
import metadata
import traceback
import path_migrate

# todo: clean out empty parent dirs.

def kill( mdj_full_path, dst, dry_run ):
    src_full_path = os.path.split( mdj_full_path )[0]
    dst_full_path = os.path.join( dst, "_"+src_full_path )
    visit_core.log( "kill%s: %s -> %s\n" % (" (not!)" if dry_run else "", src_full_path, dst_full_path) )
    if not dry_run:
        shutil.move( src_full_path, dst_full_path )
    visit_core.log( "- kill\n" )

def kill_single( file_count, full_path, data ):
    visit_core.log( "+ kill_single: %s\n" % full_path )
    if util.smells_like_json_metadata( full_path ):
        md = metadata.read_json_path( full_path )
        if metadata.is_only_db( md ):
            kill( full_path, data[3], data[2] )
    visit_core.log( "- kill_single: %s\n" % full_path )

def visit_single( file_count, full_path, data ):
    visit_core.log( "+ visit_single\n" )
    path_migrate.visit_single( file_count, full_path, data )
    kill_single( file_count, full_path, data )
    visit_core.log( "- visit_single\n" )

def usage(msg=None):
    if msg:
        visit_core.log_error("[%s]\n" % msg)
    visit_core.log_error( "usage: %s {--dryrun} <src> <dst> <chown-uid> <chown-gid>\n" % sys.argv[0] )
    visit_core.log_error( "was: %s\n" % " ".join( sys.argv ) )
    sys.exit()

if __name__ == '__main__':
    import sys
    if not sys.argv or len(sys.argv) < 4:
        usage()
    try:
        dm = visit_core.main_helper( usage )
        src = os.path.abspath( sys.argv[1] )
        dst = os.path.abspath( sys.argv[2] )
        uid = int(sys.argv[3])
        gid = int(sys.argv[4])
        f = visit_core.visit( src, dm['max_depth'], visit_single, None, (uid,gid,dm['dry_run'],dst) )
    except:
        usage(msg="args: %s" % traceback.format_exception(*sys.exc_info()))
    print( "visited %s files." % f )
