#!/usr/bin/env python

import metadata

def check_root( basedir ):
    return check_tree( basedir, basedir )

def check_tree( basedir, currentdir ):

    import os
    import os.path
    import util

    passed = True
    dirs = []
    failed = []
    data_file_count = 0

    for f in os.listdir( currentdir ):
        fullpath = os.path.join( currentdir, f )

        if os.path.isfile( fullpath ) and util.smells_like_json_metadata( fullpath ):
            data_path = util.metadata_to_data_path( fullpath )
            data_file_count += 1
            # THE MEAT...
            expected_sum = util.get_checksum_from_path( data_path )
            local_sum = util.calculate_checksum( data_path )
            # ...TAEM EHT
            if expected_sum != local_sum:
                m = metadata.read_json_path( fullpath )
                failed.append( "%s:\n %s != %s\n %s" %
                               (data_path, expected_sum, local_sum,
                                metadata.simple_format( m ) ) )
                passed = False

        elif os.path.isdir( fullpath ):
            dirs.append( fullpath )

    for d in dirs:
        (sub_count, sub_passed) = check_tree( basedir, d )
        data_file_count += sub_count
        passed &= sub_passed

    if failed:
        sys.stderr.write( "%s FAILURE\n" % len(failed) )
        row = 1
        for f in failed:
            sys.stderr.write( "%s) %s\n" % (row, f) )
            row += 1

    return ( data_file_count, passed )

if __name__ == '__main__':
    import sys
    if not sys.argv or len(sys.argv) < 2:
        sys.stderr.write( "usage: %s <storage root>\n" % sys.argv[0] )
    else:
        (count, passed) = check_root( sys.argv[1] )
        if passed:
            print "checks passed 100%"
        else:
            print "checked %s file(s)" % count
