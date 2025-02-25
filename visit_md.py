#!/usr/bin/env python

import sys
import os
import os.path
import util
import metadata
import visit_core

def usage(msg=None):
    if msg:
        visit_core.log_error( "[%s]\n" % msg )
    visit_core.log_error( "usage: %s {--dryrun} {--maxdepth N} <root> <fn>\n" % sys.argv[0] )
    visit_core.log_error( "was: %s\n" % " ".join( sys.argv ) )
    sys.exit(1)

if __name__ == '__main__':
    dm = visit_core.main_helper( usage )

    try:
        root = sys.argv[1]
        fn_str = sys.argv[2]
    except:
        usage(msg=(sys.exc_info()[0]))        

    def visit_single( file_count, full_path, data ):
        if not dm['dry_run'] and util.smells_like_json_metadata( full_path ):
            md = metadata.read_json_path( full_path )
            print eval( fn_str )

    f = visit_core.visit( root, dm['max_depth'], visit_single )
    print "visited %s file(s)" % f
