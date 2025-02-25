#!/usr/bin/python

import sys
import os
import os.path
import util
import metadata
import visit_core
from bad_path_exception import *
import traceback

def usage(msg=None):
    if msg:
        visit_core.log_error("[%s]\n" % msg)
    visit_core.log_error( "usage: %s <canonical-root-dir>\n" % sys.argv[0] )
    visit_core.log_error( "was: %s\n" % " ".join( sys.argv ) )
    sys.exit()

if __name__ == '__main__':
    dm = visit_core.main_helper( usage, False, True )
    try:
        root = sys.argv[1]
    except:
        usage(msg=(sys.exc_info()[0]))
    def visit_single( file_count, full_path, data ):
        if util.smells_like_pickled_metadata( full_path ):
            visit_core.log( "reading %s\n" % full_path )
            metadata.metadata_file_to_json_file( full_path )
    single_path = util.eat_arg( sys.argv, "single", remove=True, reqval=True )
    if single_path != None:
        visit_single( 0, single_path )
        f = 1
    else:
        f = visit_core.visit( root, dm['max_depth'], visit_single )
