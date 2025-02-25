#!/usr/bin/env python

# todo: convert to using visit_core.

import sys
import os
import os.path
import util
import metadata

def query_single( md, fn_str ):
    return eval( fn_str )

def query( dir, fn_str ):
    file_count = 0
    match_count = 0
    dirs = []

    for f in os.listdir( dir ):
        qpath = os.path.join( dir, f )

        if os.path.isfile( qpath ) and util.smells_like_json_metadata( qpath ):
            file_count += 1
            md = metadata.read_json_path( qpath )
            if( query_single( md, fn_str ) ):
                print md
                match_count += 1

        elif os.path.isdir( qpath ):
            dirs.append( qpath )

    for d in dirs:
        f, m = query( d, fn_str )
        file_count += f
        match_count += m

    return file_count, match_count

if __name__ == '__main__':
    import sys
    if util.in_sysargv( "test" ): # todo: fix.
        test()
    elif not sys.argv or len(sys.argv) != 3:
        sys.stderr.write( "usage: %s <root_dir> <fn_str 'md'->boolean>\n" % sys.argv[0] )
    else:
        file_count, match_count = query( *sys.argv[1:] )
        sys.stdout.write( "matched %s of %s\n" % ( match_count, file_count ) )

