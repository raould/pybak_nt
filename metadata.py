#!/usr/bin/env python

# todo: god hell, this should just be a real, respectable, class.
# todo: and/or i wish this was all more functionally pure, what a bunch of confused crap.
# todo: does STASHED really work?

import util
import os
import os.path
import sys
import calendar
import time
import json
import filespec
import binascii
import pickle
import copy
import hexlpathutil
import re
import visit_core

LATEST_VERSION=10 # todo: fix how versioning is even done :-(
UNKNOWN_VALUE='unknown_value' # hopefully no e.g. hosts we crawl are called that.
RAW_BYTES_ENCODING='RAW_BYTES' # see CustomEncodings.java
DEFAULT_ENCODING=RAW_BYTES_ENCODING
RUNTIME_MIGRATED_KEY='runtime_migrated' # do not include in de/seriailzation.
STASHED_KEY='stashed'
VERSION_KEY='version'
PATHS_KEY='paths'
HOSTS_KEY='hosts'
LAST_UPDATE_SEC_KEY='last-update-sec'
OLDEST_TIMESTAMP_KEY='oldest-timestamp'
EXE_KEY='exe'
FILEPATH_PARTS_KEY='filepath_parts'
DEPRECATED_FILEPATH_ENCODING_KEY='filepath_encoding'
PY_FILEPATH_ENCODING_KEY='py_filepath_encoding'
PY_PLATFORM_SYSTEM_KEY='py_platform_system'
PY_PLATFORM_UNAME_KEY='py_platform_uname'
PY_BYTEORDER_KEY='py_byteorder'
PY_PATH_SEP_KEY='py_path_sep'
PICKLE_DOTEXT='.metadata'
JSON_DOTEXT='.mdj'
DEFAULT_PATH_SEP='/'
ASCII_PATH='ascii_path'

# new metadata schema is a dict like this example:
# (see previous 'new' schema below)
#
# (note that strings in python are, i think, just
# a series of bytes which means they can represent
# things like ext{3,4} unix paths that are just bytes.
# so i am leaving them 'clear' in the python md, but
# am hexlifying for json.)
#
# { VERSION_KEY => int
#   STASHED => pre_migrated_md
#   HOSTS_KEY =>
#    { host =>
#       { PY_PLATFORM_SYSTEM_KEY => string
#         PY_PLATFORM_UNAME_KEY => string
#         PY_BYTEORDER_KEY => string
# todo: should really make another version where
# PATHS_KEY becomes HEXL_PATHS_KEY and
# FILEPATH_PARTS_KEY becomes HEXL_FILEPATH_PARTS_KEY.
# we don't know if our exported metadata did twice-hexl-ing.
#	  PATHS_KEY =>
#                 !? not sure this is all 100% accurate... ?!
#		{ clear-path in runtime metadata, hexl-path in mdj =>
#                 { LAST_UPDATE_SEC_KEY => seconds
#		    OLDEST_TIMESTAMP_KEY => seconds
#		    EXE_KEY => is_executable
#                   FILEPATH_PARTS_KEY => (clear/hexl)[path,to,file] (unfortunately, historically, optional.)
#		    PY_FILEPATH_ENCODING_KEY => 'utf-8'
#                   PY_PATH_SEP_KEY => string # clear-text. (unfortunately?!)
#                   ASCII_PATH => safe-to-print string.
# } } } }
# 
# various previous 'new' schemas in reverse chronological oder:
#
# (2) new metadata schema is a dict of the form:
# https://bitbucket.org/raould/pybak/src/f37cb029d5e0?at=default
# { hostname =>
#  { path =>
#     -- augh, the type here is still inconsistent in the extant files!
#   { LAST_UPDATE_SEC_KEY => timegm or time.struct_time
#     OLDEST_TIMESTAMP_KEY => time.struct_time
#     EXE_KEY => is_executable }
# } }
#
# (1)
# https://bitbucket.org/raould/pybak/src/f590947e7d5c?at=default
# metadata is a dict of the form:
# { hostname => { path => last_updated_timestamp } }

def log( msg ):
    sys.stdout.write( msg )

def assert_data( md ):
    try:
        for h in md[HOSTS_KEY]:
            assert_host_data( md, h )
    except KeyError, e:
        sys.stderr.write( "KeyError: %s\n" % e )
        assert False, md

def assert_host_data( md, host ):
    hostData = md[HOSTS_KEY][host]
    assert hostData, (md,host)
    assert hostData[ PY_PLATFORM_SYSTEM_KEY ], hostData
    assert hostData[ PY_PLATFORM_UNAME_KEY ], hostData
    assert hostData[ PY_BYTEORDER_KEY ], hostData
    for p in hostData[PATHS_KEY]:
        assert_path_data( md, host, p )

def assert_path_data( md, host, path ):
    pathData = md[HOSTS_KEY][host][PATHS_KEY][path]
    assert pathData, (md,host,path)
    assert isinstance( pathData, dict ), (path, type( pathData ), pathData)
    assert pathData[ LAST_UPDATE_SEC_KEY ] != None, pathData
    assert pathData[ OLDEST_TIMESTAMP_KEY ] != None, pathData
    assert pathData[ EXE_KEY ] != None, pathData
    # historically optional: assert pathData[ FILEPATH_PARTS_KEY ], pathData
    assert pathData[ PY_FILEPATH_ENCODING_KEY ], pathData
    assert pathData[ PY_PATH_SEP_KEY ], pathData

def print_vfn( md, host, path, pathData, visitFnData=None ):
    log( "%s %s %s\n" % ( host, path, pathData ) )

def visit( md, visitFn, visitFnData=None ):
    migrate_in_place( md )
    #log( "+ visit: %s\n" % md )
    for host in md[HOSTS_KEY]:
        for path in md[HOSTS_KEY][ host ][PATHS_KEY]:
            pathData = md[HOSTS_KEY][ host ][PATHS_KEY][ path ]
            visitFnData = visitFn( md, host, path, pathData, visitFnData )
    #log( "- visit: -> %s\n" % visitFnData )
    return visitFnData

def mapPaths( md, mapFn ):
    import copy
    md2 = deepcopy( md )
    for host in md[HOSTS_KEY]:
        for path in md[HOSTS_KEY][ host ][PATHS_KEY]:
            pathData = copy.deepcopy(md[HOSTS_KEY][ host ][PATHS_KEY][ path ])
            (p2,p2d) = mapFn( md2, host, path, pathData )
            md2[HOSTS_KEY][ host ][PATHS_KEY][ p2 ] = p2d
            del md2[HOSTS_KEY][ host ][PATHS_KEY][ path ] # sure hope there's no overlap!
    return md2

def get_paths( md ):
    paths = []
    for host in md[HOSTS_KEY]:
        for path in md[HOSTS_KEY][ host ][PATHS_KEY]:
            paths.append( path )
    return paths

def simple_format( md ):
    formatted = ''
    if HOSTS_KEY in md:
        for h in md[HOSTS_KEY]:
            if PATHS_KEY in md[HOSTS_KEY][h]:
                for px in md[HOSTS_KEY][h][PATHS_KEY]:
                    formatted += ("(%s: %s)" % (h,binascii.unhexlify(px)))
    return formatted

# assumes the first one found is good enough.
def get_extension( md ):
    migrate_in_place( md )
    ext = None
    for host in md[HOSTS_KEY]:
        for path in md[HOSTS_KEY][ host ][PATHS_KEY]:
            ext = util.get_extension( path )
            if ext != None:
                return ext
    return ext

def guess_mime_types( md ):
    migrate_in_place( md )
    import mimetypes
    if len(md.items()) < 1:
        return None
    else:
        def visiter( md, host, path, pathData, fnData ):
            mt = mimetypes.guess_type( path );
            if mt != None and mt[0] != None and fnData != None:
                fnData.append( mt[0] )
        r = []
        visit( md, visiter, r )
        return r if len(r) > 0 else None

def erase( mroot, checksum, length ):
    for p in [ util.get_pickled_metadata_path( mroot, checksum, length ),
               util.get_json_metadata_path( mroot, checksum, length ) ]:
        if os.path.exists( p ) and os.path.isfile( p ):
            os.remove( p )

def needs_migration( md ):
    # just update everything, to be safe/easy.
    return True

def migrate_in_place( md ):
    if md == None:
        return md
    def _migrate_in_place( md ):
        #log( "+ _migrate_in_place: %s\n" % md )
        stashed = None
        if not STASHED_KEY in md:
            stashed = deepcopy( md )
        if VERSION_KEY in md:
            migrate_versioned_in_place( md )
        else:
            migrate_pre_versioned_in_place( md )
        # filepath_parts seemes screwed up everywhere!
        md = migrate_filepath_parts( md )
        md[ RUNTIME_MIGRATED_KEY ] = True
        if stashed != None:
            md[STASHED_KEY] = stashed
        assert_data( md )
        #log( "- _migrate_in_place: %s\n" % md )
        return md

    #log("+ migrate_in_place: %s\n" % md)
    md = util.do_while(
        lambda e: (deepcopy(e[1]), _migrate_in_place(e[1])),
        lambda e: not deepequals(e[0],e[1]),
        [{}, md]
        )[1]
    #log("- migrate_in_place: %s\n" % md)
    return md # support fluid style.

def migrate_versioned_in_place( md ):
    pass

def migrate_filepath_parts( md ):
    #log("+ migrate_filepath_parts: %s\n"%md)
    md2 = deepcopy( md )
    for host in md[HOSTS_KEY]:
        for path in md[HOSTS_KEY][host][PATHS_KEY]:
            sp = hexlpathutil.to_ascii_path(path)
            md2[HOSTS_KEY][host][PATHS_KEY][path][ASCII_PATH] = sp
            if PY_PATH_SEP_KEY in md[HOSTS_KEY][host][PATHS_KEY][path]:
                sep = md[HOSTS_KEY][host][PATHS_KEY][path][PY_PATH_SEP_KEY]
                md2[HOSTS_KEY][host][PATHS_KEY][path][FILEPATH_PARTS_KEY] = path_to_parts( path, sep )
    #log("- migrate_filepath_parts: %s\n->\n%s\n" % (md, md2))
    overwrite( md2, md )
    return md

def migrate_pre_versioned_in_place( md ):
    fix_pre_versioned_in_place_1( md )
    fix_pre_versioned_in_place_2( md )
    migrate_to_version_10_in_place( md )

def fix_pre_versioned_in_place_1( md ):
    md2 = deepcopy(md)
    for host in md:
        # mistakenly had crawled ourself.
        for path in md[host]:
            # this assumes that the machine used "/" as the path seperator.
            if ("psync-o-pathics.com" in path) and ("/browse/" in path):
                del md2[host][path]
    gc_pre_versioned( md2 )
    overwrite( md2, md )
    return md

def gc_pre_versioned( md ):
    hosts = md.keys()
    for h in hosts:
        if len( md[h].keys() ) == 0:
            del md[h]

def fix_pre_versioned_in_place_2( md ):
    for h in md:
        for p in md[h]:
            # apparently we had metadatas that didn't have a dictionary under p.
            # since i'm too lazy to recall if the old value was localtime or not
            # i'm just going to ditch it entirely, in favor of dict with 'now'.
            v = md[h][p]
            if isinstance(v, int):
                md[h][p] = { LAST_UPDATE_SEC_KEY: migrate_time(time.gmtime()) }
            # some times were/are tuples, not ints, so force them to ints.
            elif isinstance(v, dict):
                for key in [ LAST_UPDATE_SEC_KEY, OLDEST_TIMESTAMP_KEY ]:
                    md[h][p][key] = migrate_time( v.get( key, None ) )

def migrate_time( t ):
    def inner( oldt ):
        if oldt == None:
            oldt = util.get_now_seconds()
        # todo: wtf is the zone for the old struct_times?
        if isinstance( oldt, time.struct_time ):
            return calendar.timegm( oldt )
        elif isinstance( oldt, tuple ):
            return calendar.timegm( oldt )
        elif isinstance( oldt, int ) or isinstance( oldt, long ):
            return oldt
        else:
            return util.get_now_seconds()
    t2 = inner( t )
    return t2

def migrate_to_version_10_in_place( md ):
    hosts = md.keys()
    md2 = { VERSION_KEY : 10,
            HOSTS_KEY : {} }
    for h in hosts:
        old_paths = md[h]
        # pop those that got moved out of PATHS_KEY to HOSTS_KEY.
        old_paths.pop( PY_PLATFORM_SYSTEM_KEY, None )
        old_paths.pop( PY_PLATFORM_UNAME_KEY, None ) 
        old_paths.pop( PY_BYTEORDER_KEY, None )
        md2[HOSTS_KEY][h] = {
            PY_PLATFORM_SYSTEM_KEY : UNKNOWN_VALUE,
            PY_PLATFORM_UNAME_KEY : UNKNOWN_VALUE,
            PY_BYTEORDER_KEY : UNKNOWN_VALUE,
            PATHS_KEY : {}
            }
        for p in old_paths:
            px = hexlpathutil.to_hexl_path(p)
            pd = copy.deepcopy( md[h][p] )
            pd.pop( DEPRECATED_FILEPATH_ENCODING_KEY, None )
            md2[HOSTS_KEY][h][PATHS_KEY][px] = pd
            for k in [ LAST_UPDATE_SEC_KEY, OLDEST_TIMESTAMP_KEY ]:
                if not k in pd:
                    pd[k] = util.get_now_seconds()
            if not EXE_KEY in pd:
                pd[EXE_KEY] = False
            pd[PY_FILEPATH_ENCODING_KEY] = md[h][p].get( DEPRECATED_FILEPATH_ENCODING_KEY, DEFAULT_ENCODING )
            pd[PY_PATH_SEP_KEY] = DEFAULT_PATH_SEP
            pd[FILEPATH_PARTS_KEY] = path_to_parts( px, pd[PY_PATH_SEP_KEY] )
    overwrite( md2, md )
    assert_data( md ) # since this is the latest version.
    return md

def path_to_parts( path, sep ):
    px = hexlpathutil.to_hexl_path( path )
    sx = hexlpathutil.to_hexl_path( sep )
    parts = px.split( sx )
    while parts[0] == "":
        del parts[0]
    return parts

def update_from_md( mroot, spec, md ):
    #log( "+ update_from_md: spec:%s, md:%s\n" % (spec, md) )
    local_md = read_both( mroot, spec.checksum, spec.length )
    # unclear which way to merge since who know which one is really newer/better.
    # i wouldn't really even trust the file timestamps on the md files.
    # just arbitrarily guessing that the local one should win.
    md2 = merge( local_md, md )
    _write_json( mroot, spec.checksum, spec.length, md2 )

def update_from_spec( mroot, spec ):
    md = read_both( mroot, spec.checksum, spec.length )
    _update_core_from_spec( md, spec )
    _write_json( mroot, spec.checksum, spec.length, md )

def _update_core_from_spec( md, spec ):
    #log( "+ _update_core_from_spec: md:%s, spec:%s\n" % (md, spec) )
    assert spec.py_platform_system != UNKNOWN_VALUE
    assert spec.py_platform_uname != UNKNOWN_VALUE
    assert spec.py_byteorder != UNKNOWN_VALUE
    migrate_in_place( md )
    #log( "1 _update_core_from_spec: %s\n" % simple_format(md) )

    if not HOSTS_KEY in md:
        md[HOSTS_KEY] = {}
    if not spec.hostname in md[HOSTS_KEY]:
        md[HOSTS_KEY][ spec.hostname ] = {
            PY_PLATFORM_SYSTEM_KEY : spec.py_platform_system,
            PY_PLATFORM_UNAME_KEY : spec.py_platform_uname,
            PY_BYTEORDER_KEY : spec.py_byteorder,
            PATHS_KEY : {}
            }
    #log( "2 _update_core_from_spec: %s\n" % simple_format(md) )

    if spec.hexl_filepath not in md[HOSTS_KEY][ spec.hostname ][PATHS_KEY]:
        md[HOSTS_KEY][ spec.hostname ][PATHS_KEY][ spec.hexl_filepath ] = {}
    pathData = md[HOSTS_KEY][ spec.hostname ][PATHS_KEY][ spec.hexl_filepath ]
    pathData[ FILEPATH_PARTS_KEY ] = spec.hexl_filepath_parts
    pathData[ PY_FILEPATH_ENCODING_KEY ] = spec.py_filepath_encoding
    pathData[ LAST_UPDATE_SEC_KEY ] = util.get_now_seconds()
    pathData[ PY_PATH_SEP_KEY ] = spec.py_path_sep
    #log( "5 _update_core_from_spec: %s\n" % simple_format(md) )

    update_oldest( pathData, spec.oldest )
    #log( "6 _update_core_from_spec: %s\n" % simple_format(md) )

    pathData[ EXE_KEY ] = spec.isexe
    #log( "7 _update_core_from_spec: %s\n" % simple_format(md) )

    remove_extraneous_relative_paths_in_place( md )
    #log( "8 _update_core_from_spec: %s\n" % simple_format(md) )

    migrate_in_place( md )
    assert_data( md )
    #log( "- _update_core_from_spec: %s\n" % md )
    return md

def update_oldest( parent, oldest ):
    oldest = migrate_time( oldest )
    if OLDEST_TIMESTAMP_KEY not in parent:
        parent[ OLDEST_TIMESTAMP_KEY ] = oldest
    else:
        prev = parent[ OLDEST_TIMESTAMP_KEY ]
        cur = oldest
        minD = min( prev, cur )
        parent[ OLDEST_TIMESTAMP_KEY ] = minD

def get_oldest( md ):
    migrate_in_place( md )
    oldest = None
    for host in md[HOSTS_KEY]:
        for path in md[HOSTS_KEY][host][PATHS_KEY]:
            for key in md[HOSTS_KEY][host][PATHS_KEY][path]:
                if key == OLDEST_TIMESTAMP_KEY:
                    t = migrate_time( md[HOSTS_KEY][host][PATHS_KEY][path][key] )
                    if oldest == None or t < oldest:
                        oldest = t
    return oldest

def remove_extraneous_relative_paths_in_place( md ):
    migrate_in_place( md )
    md2 = deepcopy( md )
    for host in md2[HOSTS_KEY]:
        if has_absolute_paths( md2, host ):
            md2 = remove_relative_paths( md2, host )
    assert_data( md2 )
    overwrite( md2, md )
    return md

def has_absolute_paths( md, host ):
    #log( "+ has_absolute_paths: %s %s\n" % (md,host) )
    migrate_in_place( md )
    def vfn( md, host, px, pathData, has ):
        sx = hexlpathutil.to_hexl_path(pathData[PY_PATH_SEP_KEY])
        has = True if px.startswith( sx ) else has
        #log( "1 has_absolute_paths: %s %s %s\n" % (has,sx,px) )
        return has
    has = visit( md, vfn, False )
    #log( "- has_absolute_paths: %s\n" % has )
    return has

def remove_relative_paths( md, host ):
    migrate_in_place( md )
    import copy
    mdc = deepcopy(md)
    p2t = mdc[HOSTS_KEY][host][PATHS_KEY]
    relatives = reduce( lambda r,e: r if e[0].startswith(hexlpathutil.to_hexl_path(e[1][PY_PATH_SEP_KEY])) else r+[e[0]], p2t.items(), [] )
    for r in relatives:
        del p2t[r]
    assert_data( mdc )
    return mdc

def deepcopy( md ):
    md2 = copy.deepcopy( md )
    md2.pop( RUNTIME_MIGRATED_KEY, None )
    return md2;

def deepequals( md1, md2 ):
    def to_list(md):
        if md == None:
            return []
        else:
            return sorted( filter( lambda e:e[0]!=RUNTIME_MIGRATED_KEY, md.items() ) )
    i1 = to_list(md1)
    i2 = to_list(md2)
    return i1 == i2

def overwrite( src, dst ):
    dst.clear()
    for k in src:
        dst[k] = src[k]

def merge( srcmd, dstmd ):
    migrate_in_place( srcmd )
    migrate_in_place( dstmd )
    if srcmd == None and dstmd != None:
        return dstmd
    if srcmd != None and dstmd == None:
        return srcmd
    newmd = deepcopy(dstmd)
    for host in srcmd[HOSTS_KEY]:
        if not host in newmd[HOSTS_KEY]:
            newmd[HOSTS_KEY][host] = srcmd[HOSTS_KEY][host]
        merge_host( srcmd[HOSTS_KEY][host], newmd[HOSTS_KEY][host] )
    remove_extraneous_relative_paths_in_place( newmd )
    assert_data( newmd )
    return newmd

def merge_host( srchost, dsthost ):
    for srcpath in srchost[PATHS_KEY]:
        if not srcpath in dsthost[PATHS_KEY]:
            dsthost[PATHS_KEY][srcpath] = srchost[PATHS_KEY][srcpath]
        else:
            srctime = srchost[PATHS_KEY][srcpath][LAST_UPDATE_SEC_KEY]
            dsttime = dsthost[PATHS_KEY][srcpath][LAST_UPDATE_SEC_KEY]
            if dsttime is None or srctime > dsttime:
                dsthost[PATHS_KEY][srcpath] = srchost[PATHS_KEY][srcpath]

def is_only_db( md ):
    # e.g. /canonical/00/00/03/2c/9a/df/c6/36/6d/80/cb/85/73/ef/8a/cf
    p_count = 0
    db_count = 0
    for h in md[HOSTS_KEY]:
        for px in md[HOSTS_KEY][h][PATHS_KEY]:
            p_count = p_count+1
            match = re.match( ".*/canonical/../../../../../../../../../../../../../../../../.*", hexlpathutil.to_clear_path(px) )
            #log( "is_only_db: %s %s %s\n" % (h,px,match) )
            if match != None:
                db_count = db_count+1
    db_percent = 0 if p_count == 0 else 100*db_count/float(p_count)
    log( "is_only_db: %s (%s/%s) = %s%%\n" % (h,db_count,p_count,db_percent) )
    return p_count > 0 and p_count == db_count

def metadata_file_to_json_file( file_path ):
    md = read_pickled_path( file_path )
    file_path_json = file_path.replace( PICKLE_DOTEXT, JSON_DOTEXT )
    write_json_path( md, file_path_json )

def _write( mroot, checksum, length, md ):
    migrate_in_place( md )
    p = util.get_pickled_metadata_path( mroot, checksum, length )
    write_path( md, p )
    return p

def write_path( md, path ):
    migrate_in_place( md )
    del md[ RUNTIME_MIGRATED_KEY ]
    import pickle
    util.ensure_parent_path( path )
    mdf = open( path, "w" )
    pickle.dump( md, mdf )
    mdf.close()
    write_json_path( md, path.replace( PICKLE_DOTEXT, JSON_DOTEXT ) )

def _write_json( mroot, checksum, length, md ):
    migrate_in_place( md )
    p = util.get_json_metadata_path( mroot, checksum, length )
    write_json_path( md, p )
    return p

def to_json_path( path ):
    path = re.sub("%s$"%PICKLE_DOTEXT, "", path)
    path = re.sub("%s$"%JSON_DOTEXT, "", path)
    jp = "%s%s" % (path, JSON_DOTEXT)
    return jp

def write_json_path( md, path ):
    migrate_in_place( md )
    del md[ RUNTIME_MIGRATED_KEY ]
    assert JSON_DOTEXT in path, path
    util.ensure_parent_path( path )
    util.write_replace( path, "%s\n" % to_json(md), True )

def to_json( md ):
    migrate_in_place( md )
    del md[ RUNTIME_MIGRATED_KEY ]
    mdh = hexlify_md( md )
    return json.dumps( mdh, separators=(',', ':') )

def _hx_md( md, xfn ):
    def hxfn( md, host, path, pathData ):
        p2 = xfn( path )
        pd2 = copy.deepcopy( pathData )
        if FILEPATH_PARTS_KEY in pathData:
            a = pathData[FILEPATH_PARTS_KEY]
            fp2 = map(lambda e: xfn(e), a)
            pd2[FILEPATH_PARTS_KEY] = fp2
        return (p2, pd2)
    md2 = mapPaths( md, hxfn )
    return md2

def hexlify_md( md ):
    return _hx_md( md, binascii.hexlify )

def unhexlify_md( hmd ):
    return _hx_md( hmd, binascii.unhexlify )

def read_both( mroot, checksum, length ):
    p_md = {}
    j_md = {}

    p_path = util.get_pickled_metadata_path( mroot, checksum, length )
    if os.path.isfile( p_path ):
        p_md = read_pickled_path( p_path )

    j_path = util.get_json_metadata_path( mroot, checksum, length )
    if os.path.isfile( j_path ):
        j_md = read_json_path( j_path )

    md = merge( j_md, p_md )
    assert_data( md )
    return md

def read_both_in_path( path ):
    md = {}
    if path == None:
        return md
    path = re.sub("%s$"%PICKLE_DOTEXT, "", path)
    path = re.sub("%s$"%JSON_DOTEXT, "", path)
    paths = [
        "%s%s" % (path, PICKLE_DOTEXT),
        "%s" % (path),
        "%s%s" % (path, JSON_DOTEXT)
    ]
    mds = []
    for p in paths:
        try:
            mdp = read_pickled_path( p )
            mds.append( mdp )
        except:
            pass
        try:
            mdj = read_json_path( p )
            mds.append( mdj )
        except:
            pass
    for m in mds:
        md = merge(m, md)
    return md

def read_pickled_path_nomigrate( mdpath ):
    util.ensure_parent_path( mdpath )
    if not util.smells_like_pickled_metadata( mdpath ):
        sys.stderr.write( "not pickled file extension: %s\n" % mdpath )
    if not os.path.isfile( mdpath ):
        raise Exception, ( "no such file / not a file: %s\n" % mdpath )
    if os.path.getsize( mdpath ) <= 0:
        return {}
    mdf = open( mdpath, "r" )
    try:
        md = pickle.load( mdf )
    except Exception, e:
        sys.stderr.write( "failed to pickle.load(): %s\n" % mdpath )
        raise e
    finally:
        mdf.close()
    return md

def read_pickled_path( mdpath ):
    md = read_pickled_path_nomigrate( mdpath )
    # todo: doing these here is kind of fubar!
    migrate_in_place( md )
    assert_data( md )
    return md

def read_json_path_nomigrate( mdpath ):
    util.ensure_parent_path( mdpath ) # don't recally why i do this.
    if not util.smells_like_json_metadata( mdpath ):
        sys.stderr.write( "not json file extension: %s\n" % mdpath )
    if not os.path.isfile( mdpath ):
        sys.stderr.write( "not a file: %s\n" % mdpath )
        raise Exception
    if os.path.getsize( mdpath ) <= 0:
        return {}
    mdf = open( mdpath, "r" )
    try:
        mdx = json.load( mdf )
    except Exception, e:
        sys.stderr.write( "failed to json.load(): %s\n" % mdpath )
        raise e
    finally:
        mdf.close()
    return mdx

def read_json_path( mdpath ):
    mdx = read_json_path_nomigrate( mdpath )
    # todo: doing these here is kind of fubar!
    md = unhexlify_md( mdx )
    assert_data( md )
    migrate_in_place( md )
    return md

#
#
#

help_tests_counter=0
def help_tests_write_read(md):
    p = _write( "/tmp", "foobar_" + str(help_tests_counter), "667", md )
    assert os.path.exists( p ), p
    md2 = read_pickled_path( p )
    md.pop( RUNTIME_MIGRATED_KEY, None )
    md.pop( STASHED_KEY, None )
    md2.pop( RUNTIME_MIGRATED_KEY, None )
    md2.pop( STASHED_KEY, None )
    assert md == md2, "%s" % util.dict_diff(md, md2)

def hx(p):
    return binascii.hexlify(p)

g_sep = "%"
g_sepx = binascii.hexlify(g_sep)
g_ct = (2011, 9, 23, 23, 2, 3, 4, 266, 0)
g_p = g_sep+"0"
g_px = binascii.hexlify(g_p)
g_p2 = g_sep+"A"+g_sep+"B"
g_px2 = binascii.hexlify(g_p2)
g_r = "0"
g_rx = binascii.hexlify(g_r)
g_md = {
    VERSION_KEY: 10,
    HOSTS_KEY: {
        'h1': {
            PY_PLATFORM_SYSTEM_KEY: 'ppsk',
            PY_PLATFORM_UNAME_KEY: 'puk',
            PY_BYTEORDER_KEY: 'little',
            PATHS_KEY: {}
            }
        }
    }

def update_core_helper_test( md, h, p, o, i, fpp=None ):
    px = hexlpathutil.to_hexl_path( p )
    hxfp = hexlpathutil.hexl_path_to_hexl_list(px,g_sep) if fpp == None else fpp
    log("+ update_core_helper_test: %s, %s, %s->%s->%s, %s, %s\n" % (md, h, p, px, hxfp, o, i))
    fs = filespec.FileSpec( hostname=h,
                            py_platform_system="pps",
                            py_platform_uname="uname",
                            py_filepath_encoding="UTF-7", # real, but scary.
                            py_byteorder="little",
                            py_path_sep=g_sep,
                            hexl_filepath=px,
                            hexl_filepath_parts=hxfp,
                            checksum=42,
                            length=1,
                            is_canonical=False,
                            is_metadata=False,
                            oldest=o,
                            isexe=i )
    log("1 update_core_helper_test: %s\n" % fs)
    md = _update_core_from_spec( md, fs )
    log("- update_core_helper_test: %s\n" % md)
    return md

def test_remove_extraneous_relative_paths():
    md = deepcopy(g_md)
    update_core_helper_test( md, "h1", g_r, g_ct, False )
    update_core_helper_test( md, "h1", g_r, g_ct, False )
    update_core_helper_test( md, "h1", g_p, g_ct, False )
    assert not g_rx in md[HOSTS_KEY]["h1"][PATHS_KEY], md
    assert g_px in md[HOSTS_KEY]["h1"][PATHS_KEY], md
    help_tests_write_read(md)

def test_remove_extraneous_relative_paths_immutable():
    md = deepcopy(g_md)
    update_core_helper_test( md, "h1", g_r, g_ct, False )
    update_core_helper_test( md, "h1", g_p, g_ct, False )
    assert not g_rx in md[HOSTS_KEY]["h1"][PATHS_KEY], md
    help_tests_write_read(md)

def test_merge_AbsOntoRel():
    abspath = g_sep+"abs"+g_sep+"rel1"
    md1 = deepcopy(g_md)
    update_core_helper_test( md1, "h1", abspath, g_ct, False )
    md2 = deepcopy(g_md)
    update_core_helper_test( md2, "h1", "rel1", g_ct, False )
    md3 = merge( md1, md2 )
    assert not hx("rel1") in md3[HOSTS_KEY]["h1"][PATHS_KEY], md3
    assert hx(abspath) in md3[HOSTS_KEY]["h1"][PATHS_KEY], md3
    help_tests_write_read(md1)
    help_tests_write_read(md2)
    help_tests_write_read(md3)

def test_merge_RelOntoAbs():
    abspath = g_sep+"abs"+g_sep+"rel1"
    md1 = deepcopy(g_md)
    update_core_helper_test( md1, "h1", "rel1", g_ct, False )
    md2 = deepcopy(g_md)
    update_core_helper_test( md2, "h1", abspath, g_ct, False )
    md3 = merge( md1, md2 )
    assert not hx("rel1") in md3[HOSTS_KEY]["h1"][PATHS_KEY], md3
    assert hx(abspath) in md3[HOSTS_KEY]["h1"][PATHS_KEY], md3
    help_tests_write_read(md1)
    help_tests_write_read(md2)
    help_tests_write_read(md3)
    
def test_merge_host_A():
    md1 = migrate_in_place( { 'h1' : { g_p : { LAST_UPDATE_SEC_KEY : 0, EXE_KEY : True } } } )
    md2 = migrate_in_place( { 'h1' : { g_p : { LAST_UPDATE_SEC_KEY : 1, EXE_KEY : False } } } )
    md3 = merge( md1, md2 )
    assert not md3[HOSTS_KEY]['h1'][PATHS_KEY][g_px][EXE_KEY], md3

def test_merge_host_B():
    md1 = migrate_in_place( { 'h1' : { g_p : { LAST_UPDATE_SEC_KEY : 0, EXE_KEY : False } } } )
    md2 = migrate_in_place( { 'h1' : { g_p : { LAST_UPDATE_SEC_KEY : 1, EXE_KEY : True } } } )
    md3 = merge( md1, md2 )
    assert md3[HOSTS_KEY]['h1'][PATHS_KEY][g_px][EXE_KEY], md3

def test_exe():
    md = deepcopy(g_md)
    update_core_helper_test( md, "thost", g_p, g_ct, True )
    assert md[HOSTS_KEY][ "thost" ][PATHS_KEY][g_px][ "exe" ]
    help_tests_write_read(md)

# todo: who should really win, here?!
def test_double_exe():
    md = deepcopy(g_md)
    update_core_helper_test( md, "thost", g_p, g_ct, True )
    update_core_helper_test( md, "thost", g_p, g_ct, False )
    assert not md[HOSTS_KEY][ "thost" ][PATHS_KEY][g_px][ "exe" ]
    help_tests_write_read(md)

def test_migrate_filepath_parts_A():
    md = update_core_helper_test( {}, "h1", g_p2, g_ct, True, [g_px2] )
    fp = md[HOSTS_KEY]["h1"][PATHS_KEY][g_px2][FILEPATH_PARTS_KEY]
    assert len(fp) == 2, md
    assert fp == [hx('A'),hx('B')], md

def test_migrate_in_place_lastupdate():
    md = migrate_in_place( { 'h1': { 'p1': 666 } } )
    assert not md[HOSTS_KEY]['h1'][PATHS_KEY][hx('p1')] == 666, md
    assert md[HOSTS_KEY]['h1'][PATHS_KEY][hx('p1')][LAST_UPDATE_SEC_KEY] != 666

def test_migrate_in_place_oldest():
    import calendar
    md = {}
    update_core_helper_test( md, "thost", g_p, g_ct, True )
    go = get_oldest( md )
    io = md[HOSTS_KEY]["thost"][PATHS_KEY][g_px][ OLDEST_TIMESTAMP_KEY ]
    to = migrate_time( g_ct )
    assert go == io
    assert io == to

def test_migrate_in_place_encoding():
    md = migrate_in_place( { 'h': { 'p': { DEPRECATED_FILEPATH_ENCODING_KEY : "xyzpdq" } } } )
    assert not DEPRECATED_FILEPATH_ENCODING_KEY in md[HOSTS_KEY]['h'][PATHS_KEY][hx('p')], md
    assert md[HOSTS_KEY]['h'][PATHS_KEY][hx('p')][PY_FILEPATH_ENCODING_KEY] == "xyzpdq", md

def test_migrate_in_place_versionA():
    md = migrate_in_place( { 'h' : { 'p' : { LAST_UPDATE_SEC_KEY : 42 } } } )
    assert not 'p' in md, md
    assert not hx('p') in md, md
    assert not 'p' in md[HOSTS_KEY], md
    assert not hx('p') in md[HOSTS_KEY], md
    assert not 'p' in md[HOSTS_KEY]['h'], md
    assert not hx('p') in md[HOSTS_KEY]['h'], md
    assert hx('p') in md[HOSTS_KEY]['h'][PATHS_KEY], md

def test_fix_mistakes_browse():
    md = migrate_in_place( { 'h' : { '/psync-o-pathics.com/browse/bar': { LAST_UPDATE_SEC_KEY: 42 } } } )
    assert len(md[HOSTS_KEY].keys()) == 0

def test_fix_mistakes_root1():
    md = migrate_in_place( { 'h' : { '/bar': { LAST_UPDATE_SEC_KEY: 42 } } } )
    assert len(md[HOSTS_KEY].keys()) == 1
    assert len(md[HOSTS_KEY]['h']) == 4
    assert md[HOSTS_KEY]['h'][PATHS_KEY][hx('/bar')][LAST_UPDATE_SEC_KEY] == 42

def test_fix_mistakes_root2():
    md = migrate_in_place( { 'h' :
           {'/bar/baz':
            {LAST_UPDATE_SEC_KEY:43},
            '/bar':
            {LAST_UPDATE_SEC_KEY:42}
            }
           } )
    assert len(md[HOSTS_KEY].keys()) == 1
    assert len(md[HOSTS_KEY]['h']) == 4
    assert md[HOSTS_KEY]['h'][PATHS_KEY][hx('/bar/baz')][LAST_UPDATE_SEC_KEY] == 43

# TODO: is this the right solution to the problem?
def test_fix_mistakes_msdos():
    p = 'c:\\documents and settings\\foobar.jpg'
    md = migrate_in_place( { 'h' : { p : { LAST_UPDATE_SEC_KEY : 42 } } } )
    assert len(md[HOSTS_KEY].keys()) == len(md[HOSTS_KEY].keys())
    assert len(md[HOSTS_KEY]['h']) == 4
    assert md[HOSTS_KEY]['h'][PATHS_KEY][hx(p)][LAST_UPDATE_SEC_KEY] == 42

def test_oldest():
    import calendar
    md = deepcopy(g_md)
    update_core_helper_test( md, "thost", g_p, g_ct, True )
    update_core_helper_test( md, "thost", g_p, (2010, 9, 23, 23, 2, 3, 4, 266, 0), False )
    actual = md[HOSTS_KEY]["thost"][PATHS_KEY][hx(g_p)][ OLDEST_TIMESTAMP_KEY ]
    expected = migrate_time( calendar.timegm( (2010, 9, 23, 23, 2, 3, 4, 266, 0) ) )
    assert actual == expected, "%s / %s / %s" % (md, actual, expected)

# 'impossible' due to binary filename, and wrong '%' separator.
IMPOSSIBLE_LINUX = "bin%\xd4v\xcc\xaf\x19"

def test_roundtrip_hexlify_md_A():
    md = deepcopy(g_md)
    hmd = update_core_helper_test( md, "h1", IMPOSSIBLE_LINUX, g_ct, True )
    tmp = unhexlify_md( hmd )
    hmd2 = hexlify_md( tmp )
    hmd.pop( RUNTIME_MIGRATED_KEY, None )
    hmd.pop( STASHED_KEY, None )
    hmd2.pop( RUNTIME_MIGRATED_KEY, None )
    hmd2.pop( STASHED_KEY, None )
    assert hmd == hmd2, "%s\n%s\n%s"%(util.dict_diff(hmd,hmd2),hmd,hmd2)

def test_json_roundtrip_LAST_UPDATE_SEC_KEY():
    md = migrate_in_place( { 'h1' : { g_p : { LAST_UPDATE_SEC_KEY:7 } } } )
    p = "/tmp/test4.mdj"
    write_json_path( md, p )
    md2 = read_json_path( p )
    assert md[HOSTS_KEY]['h1'][PATHS_KEY][g_px][LAST_UPDATE_SEC_KEY] == md2[HOSTS_KEY]['h1'][PATHS_KEY][g_px][LAST_UPDATE_SEC_KEY], "%s\n%s"%(md,md2)

def test_json_roundtrip_OLDEST_TIMESTAMP_KEY():
    md = migrate_in_place( { 'h1' : { g_p : { OLDEST_TIMESTAMP_KEY:7 } } } )
    p = "/tmp/test3.mdj"
    write_json_path( md, p )
    md2 = read_json_path( p )
    assert md[HOSTS_KEY]['h1'][PATHS_KEY][g_px][OLDEST_TIMESTAMP_KEY] == md2[HOSTS_KEY]['h1'][PATHS_KEY][g_px][OLDEST_TIMESTAMP_KEY], "%s\n%s"%(md,md2)

def test_json_roundtrip_PY_FILEPATH_ENCODING_KEY_KEY_lowers():
    md = deepcopy(g_md)
    update_core_helper_test( md, 'h1', g_p, g_ct, False )
    p = "/tmp/test1.mdj"
    write_json_path( md, p )
    md2 = read_json_path( p )
    assert md2[HOSTS_KEY]['h1'][PATHS_KEY][g_px][PY_FILEPATH_ENCODING_KEY] == 'utf-7', md2

def test_filepath_encoding_lowers():
    md = deepcopy(g_md)
    update_core_helper_test( md, 'h1', g_p, g_ct, False )
    assert md[HOSTS_KEY]['h1'][PATHS_KEY][g_px][PY_FILEPATH_ENCODING_KEY] == 'utf-7', md

def test_has_absolute_paths_A():
    mdYes = deepcopy(g_md)
    log( "test_has_absolute_paths_A(): before: %s\n" % mdYes )
    update_core_helper_test( mdYes, 'h1', g_p, g_ct, False )
    log( "test_has_absolute_paths_A(): after: %s\n" % mdYes )
    has = has_absolute_paths( mdYes, 'h1' )
    assert has, mdYes

def test_has_absolute_paths_B():
    mdNo = deepcopy(g_md)
    update_core_helper_test( mdNo, 'h1', g_r, g_ct, False )
    has = has_absolute_paths( mdNo, 'h1' )
    assert not has, mdNo

def test_guess_path_parts():
    p = '//c/p1/p2 /p3'
    md = { 'h1' : { p : {} } }
    migrate_in_place( md )
    parts = md[HOSTS_KEY]['h1'][PATHS_KEY].items()[0][1][FILEPATH_PARTS_KEY]
    assert parts[0] != "", parts

def test_is_only_db_A():
    p = '/canonical/00/00/03/2c/9a/df/c6/36/6d/80/cb/85/73/ef/8a/cf/xyzpdq'
    md = { 'h1' : { p : {} } }
    migrate_in_place( md )
    assert is_only_db(md), md

def test_is_only_db_B():
    p = '/canonical/00/03/2c/9a/df/c6/36/6d/80/cb/85/73/ef/8a/cf/xyzpdq'
    md = { 'h1' : { p : {} } }
    migrate_in_place( md )
    assert not is_only_db(md), md

def test():
    for tfn in [
        test_is_only_db_A,
        test_is_only_db_B,
        test_roundtrip_hexlify_md_A,
        test_guess_path_parts,
        test_has_absolute_paths_A,
        test_has_absolute_paths_B,
        test_filepath_encoding_lowers,
        test_json_roundtrip_PY_FILEPATH_ENCODING_KEY_KEY_lowers,
        test_json_roundtrip_LAST_UPDATE_SEC_KEY,
        test_json_roundtrip_OLDEST_TIMESTAMP_KEY,
        test_remove_extraneous_relative_paths,
        test_remove_extraneous_relative_paths_immutable,
        test_merge_AbsOntoRel,
        test_merge_RelOntoAbs,
        test_merge_host_A,
        test_merge_host_B,
        test_exe,
        test_double_exe,
        test_migrate_filepath_parts_A,
        test_migrate_in_place_lastupdate,
        test_migrate_in_place_oldest,
        test_migrate_in_place_encoding,
        test_migrate_in_place_versionA,
        test_fix_mistakes_browse,
        test_fix_mistakes_root1,
        test_fix_mistakes_root2,
        test_fix_mistakes_msdos,
        test_oldest,
        ]:
        print tfn
        tfn()
    print "tests passed"

def read_and_dump( path ):
    if util.smells_like_pickled_metadata( path ):
        md = read_pickled_path( path )
        print( md )
    if util.smells_like_json_metadata( path ):
        md = read_json_path( path )
        print( md )

def dump():
    if len(sys.argv) != 3:
        print "missing file path argument"
        sys.exit(1)
    path = sys.argv[2]
    read_and_dump( path )

def dump_old():
    if len(sys.argv) != 3:
        print "missing <root> path argument"
        sys.exit(1)
    path = sys.argv[2]
    def visit_file( file_count, full_path, data ):
        omd = {}
        if not util.smells_like_any_metadata( path ):
            return
        if util.smells_like_pickled_metadata( path ):
            md = read_pickled_path( path )
            if STASHED_KEY in md:
                omd = md[STASHED_KEY]
        if util.smells_like_json_metadata( path ):
            omd = read_json_path( path )
        if (not VERSION_KEY in omd or int(omd[VERSION_KEY]) < 10) \
                and (len(omd) > 0):
            sys.stdout.write( omd )
        else:
            sys.stdout.write('.')
    visit_core.visit(
        "/home/pybak/canonical",
        None,
        visit_file
        )

if __name__ == '__main__':
    import sys
    if util.eat_arg( sys.argv, "test" ):
	test()
    elif util.eat_arg( sys.argv, "dump" ):
        dump()
    elif util.eat_arg( sys.argv, "dumpold" ):
        dump_old()
    else:
        log( "usage: %s {--test | --dump <path-to-md> | --dumpold <root>}\n" % sys.argv[0] )
