#!/usr/bin/env python

import sys
import os
import os.path
import shutil
import util
import metadata
import visit_core

def usage(msg=None):
    if msg:
        visit_core.log_error( "[%s]\n" % msg )
    visit_core.log_error( "usage: %s {--dry-run} {--max-depth N} <root>\n" % sys.argv[0] )
    visit_core.log_error( "was: %s\n" % " ".join( sys.argv ) )
    sys.exit(1)

if __name__ == '__main__':
    dm = visit_core.main_helper( usage )

    try:
        root = sys.argv[1]
    except:
        usage(msg=(sys.exc_info()[0]))

    def clean_path( parent, checksum, length ):
        visit_core.log( "cleaning %s, %s, %s\n" % (parent, checksum, length) )
        tail = "%s_%s" % (checksum, length)
        dp = os.path.join(parent, tail)
        mpp = os.path.join(parent, "%s%s" % (tail, metadata.PICKLE_DOTEXT))
        mjp = os.path.join(parent, "%s%s" % (tail, metadata.JSON_DOTEXT))
        for p in [dp, mpp, mjp]:
            visit_core.log("p = %s\n" % p)
            if not dm['dry_run']:
                #util.remove(p)
                if os.path.exists(p):
                    os.rename(p, "%s%s" % (p, ".rm"))

    def visit_single( file_count, full_path, data ):
        if util.smells_like_browse( full_path ):
            (checksum, length) = util.get_checksum_length_from_path( full_path )
            (parent, _) = os.path.split( full_path )
            clean_path(parent, checksum, length)

    f = visit_core.visit( root, dm['max_depth'], visit_single )
    print "visited %s file(s)" % f
