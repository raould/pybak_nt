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

    def visit_single( file_count, full_path, data ):
        if util.smells_like_pickled_metadata( full_path ):
            clean_path( full_path )
        elif util.smells_like_json_metadata( full_path ):
            clean_path( full_path )

    def read_both( root, md_path ):
        c = util.get_checksum_from_path( md_path )
        l = util.get_length_from_path( md_path )
        assert c != None
        assert l != None
        md = metadata.read_both( root, c, l )
        md2 = metadata.fix_mistakes( md )
        return ( md2, util.get_data_path( root, c, l ) )

    def clean_path( path ):
        visit_core.log( "cleaning %s\n" % path )
        ( md, data_path ) = read_both( root, path )
        json_path = util.data_to_json_metadata_path( data_path )
        pickled_path = util.data_to_pickled_metadata_path( data_path )
        if not dm['dry_run']:
            if not os.path.exists( data_path ):
                visit_core.log( "nuking empyt-data path\n" );
                util.remove( json_path )
                util.remove( pickled_path )
                shutil.rmtree( os.path.split(data_path)[0], True )
            elif md == None or len(md.keys()) == 0:
                visit_core.log( "skipping empty md (it has a data file)\n" )
            else:
                visit_core.log( "doing cleaning\n" )
                metadata.write_json_path( md, json_path )
                assert os.path.exists( json_path )
                if os.path.exists( pickled_path ):
                    util.remove( pickled_path )

    f = visit_core.visit( root, dm['max_depth'], visit_single )
    print "visited %s file(s)" % f
