#!/usr/bin/env python
import os
import os.path
import shutil
import util
import visit_core
import metadata
import traceback

### TODO: use visit_core?

import logging
gLogger = logging.getLogger("pybak-merge-canonicals")
assert not gLogger == None
hdlr = logging.FileHandler("/tmp/pybak-merge-canonicals.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
gLogger.addHandler(hdlr)
gLogger.setLevel(logging.INFO)

def log_error( msg ):
    sys.stderr.write( msg )
    gLogger.error( msg )

def log( msg ):
    sys.stdout.write( msg )
    gLogger.info( msg )

def merge_dst( s1mp, s2mp, dst, dry_run ):
    # 'dst' is a root directory.

    mid1p = os.path.sep.join(util.extract_parent_path_mids( s1mp ))
    mid2p = os.path.sep.join(util.extract_parent_path_mids( s2mp ))
    assert mid1p == mid2p, [mid1p, mid2p]
    assert mid1p != None, [s1mp, mid1p]

    s1dp = util.metadata_to_data_path( s1mp )
    s2dp = util.metadata_to_data_path( s2mp )

    (_, mdname) = os.path.split( s1mp )
    dstmp = metadata.to_json_path(os.path.sep.join([dst, mid1p, mdname]))
    dstdp = util.metadata_to_data_path( dstmp )
    log( "merge_dst(): %s %s\n" % (dstmp, dstdp) )

    util.ensure_parent_path( dstmp )
    merge_md( s1mp, s2mp, dry_run, dstmp )
    ok = check_d( s1dp, s2dp, dry_run, dstdp )
    if not ok:
        erase_dst( dstdp )
    else:
        assert_all( s1mp, s1dp, s2mp, s2dp, dstmp, dstdp )

def erase_dst( dstdp ):
    pdir = os.path.dirname( dstdp )
    files = [dstdp, util.data_to_pickled_metadata_path(dstdp), util.data_to_json_metadata_path(dstdp)]
    for f in files:
        if os.path.exists(f):
            os.remove(f)

def assert_all( s1mp, s1dp, s2mp, s2dp, dstmp, dstdp ):
    assert os.path.exists( s1mp ) or os.path.exists( s2mp ), [s1mp, s1dp, s2mp, s2dp, dstmp, dstdp]
    assert os.path.exists( dstmp ), [s1mp, s1dp, s2mp, s2dp, dstmp, dstdp]
    if os.path.exists( s1dp ) or os.path.exists( s2dp ):
        assert os.path.exists( dstdp ), [s1mp, s1dp, s2mp, s2dp, dstmp, dstdp]

def merge_md( s1mp, s2mp, dry_run, dstmp ):
    log( "merge_md(): -> %s\n" % dstmp )
    if not dry_run:
        dm = None
        s1m = None
        s2m = None
        if os.path.exists( dstmp ):
            dm = metadata.read_both_in_path( dstmp )
        if os.path.exists( s1mp ):
            s1m = metadata.read_both_in_path( s1mp )
        if os.path.exists( s2mp ):
            s2m = metadata.read_both_in_path( s2mp )
        mm = metadata.merge( s1m, dm )
        mm = metadata.merge( s2m, mm )
        metadata.write_json_path( mm, dstmp )

# when doing copy/merge, check the data file
# checksums in case the canonical one is corrupt
# and replace with src one as necessary.
def check_d( s1dp, s2dp, dry_run, dstdp ):
    log( "check_d()\n" )
    if (not os.path.exists(s1dp)) and (not os.path.exists(s2dp)):
        log( "check_d(): no sources exist\n" )
        return False
    if util.smells_like_browse(s1dp) and util.smells_like_browse(s2dp):
        log( "check_d(): both sources smell like browse" )
        return False

    ex1 = util.get_checksum_from_path( s1dp )
    ex2 = util.get_checksum_from_path( s2dp )
    exD = util.get_checksum_from_path( dstdp )
    assert ex1 == ex2, [ex1, ex2]
    assert ex1 == exD, [ex1, exD]
    log( "check_d(): %s, %s, %s\n" % (ex1, ex2, exD) )
    
    if os.path.exists( dstdp ):
        d = util.calculate_checksum( dstdp )
        log( "check_d(): %s\n" % d )
        # skip if already ok.
        if d == ex1:
            return True
    
    fromd = None
    sum1 = util.calculate_checksum( s1dp )
    sum2 = util.calculate_checksum( s2dp )
    if (sum1 == sum2):
        fromd = s1dp
    else:
        if (sum1 == ex1):
            fromd = s1dp
        elif (sum2 == ex2):
            fromd = s2dp
    if fromd == None:
        log_error( "no good data for %s (%s, %s, %s, %s, %s)\n" % (s1dp, sum1, sum2, ex1, ex2, exD) )
        return False
    else:
        log( "check_d(): copy good %s\n" % fromd )
        if not dry_run:
            assert os.path.exists( fromd )
            assert os.path.getsize( fromd ) > 0
            shutil.copyfile( fromd, dstdp )
            assert os.path.exists( dstdp )
        return True

def merge_12_flat(s1, s2, dst, dry_run):
    dirs = []
    s1pp = util.extract_parent_path_mids( s1 )
    s2pp = util.extract_parent_path_mids( s2 )
    assert s1pp == s2pp, [[s1,s1pp], [s2,s2pp]]
    log( "+s1=%s\n s2=%s\n  d=%s\n" % (s1, s2, dst) )
    for f in os.listdir( s1 ):
        s1p = os.path.join( s1, f )
        s2p = os.path.join( s2, f )
        # todo: also support pickled metadata.
        if os.path.isfile( s1p ) and util.smells_like_any_metadata( s1p ):
            log( "+s1p=%s\n s2p=%s\n dst=%s" % ( s1p, s2p, dst ) )
            merge_dst( s1p, s2p, dst, dry_run )
        elif os.path.isdir( s1p ):
            dirs.append( [s1p, s2p] )
    return dirs

def merge_12(s1, s2, dst, dry_run):
    dirs = merge_12_flat(s1, s2, dst, dry_run)
    while len(dirs) > 0:
        dp = dirs[0]
        d2 = merge_12_flat(dp[0], dp[1], dst, dry_run)
        dirs = d2 + dirs[1:]

def merge( s1, s2, dst, dry_run ):
    log( "merge(%s, %s, %s, %s)\n" % ( s1, s2, dst, dry_run ) )
    merge_12( s1, s2, dst, dry_run )
#    merge_12( s2, s1, dst, dry_run )

def usage(msg=None):
    if msg:
        log_error("[%s]\n" % msg)
    log_error( "usage: %s {--dryrun} <src1> <src2> <dst>\n" % sys.argv[0] )
    log_error( "was: %s\n" % " ".join( sys.argv ) )
    sys.exit()

def test():
    sys.stderr.write("we have no test()\n")
    sys.exit()

if __name__ == '__main__':
    import sys
    if util.eat_arg( sys.argv, "test" ):
        test()
    else:
        try:
            dm = visit_core.main_helper( usage )
            dry_run = dm['dry_run']
            src1 = os.path.abspath( sys.argv[1] )
            src2 = os.path.abspath( sys.argv[2] )
            dst = os.path.abspath( sys.argv[3] )
            merge( src1, src2, dst, dry_run )
        except:
            usage(msg="args: %s" % traceback.format_exception(*sys.exc_info()))
