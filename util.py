#!/usr/bin/env python

# todo: this can't really work on the server side,
# only on the client side, due to e.g. os.path.sep.

import sys
try:
    import hashlib as csm
except ImportError:
    import md5 as csm
import re
import os
import os.path
import shutil
import traceback
import time
import calendar
import logging
import inspect
import metadata
import exts
import binascii

gChecksumSplitLength = 2
WEB_MODIFIER = 'web'
WEB_SIZE = 1024

def log( msg ):
    sys.stdout.write( msg )

class AlreadyCompleted( Exception ):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

class ChecksumMismatch( Exception ):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)

def require_args_or_die( required ):
    if not sys.argv or len(sys.argv) < len(required):
        msg = [sys.argv[0]]
        msg.extend( required )
        msg = " ".join( msg )
        sys.stderr.write( "usage: %s\n" % msg )
        sys.exit(1)

def do_while( fnBody, fnTest, data=None ):
    data = fnBody(data)
    while( fnTest(data) ):
        data = fnBody(data)
    return data

# kwargs:
# nodash
# reqval
# remove
def eat_arg( args, arg, **kwargs ):
    import re
    raw_name = re.sub( "^-+", "", str(arg) )

    if 'nodash' in kwargs and kwargs['nodash'] == True:
        no_dash = eat_arg_core( args, "%s" % raw_name, **kwargs )
    else:
        no_dash = None

    one_dash = eat_arg_core( args, "-%s" % raw_name, **kwargs )
    two_dash = eat_arg_core( args, "--%s" % raw_name, **kwargs )

    if no_dash:
        return no_dash
    elif one_dash:
        return one_dash
    else:
        return two_dash

def eat_arg_core( args, arg, **kwargs ):
    if not arg in args:
        return None
    reqarg = 'reqval' in kwargs and kwargs['reqval'] == True
    consume = 'remove' in kwargs and kwargs['remove'] == True
    if not reqarg:
        value = True
    else:
        i = args.index(arg)+1
        if len(args) < i+1:
            sys.stderr.write( "missing value for '%s'\n" % arg )
            sys.exit(1)
        value = args[i]
        if consume:
            args.pop( i )
    if consume:
        args.remove( arg )
    return value

def extract_callers():
    c = []
    s = traceback.extract_stack()
    for i in range( 0, (len(s)-2) ):
        c.append( s[i][2] )
    return c

def uniq(seq, idfun=None):
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result

def remove( path ):
    if os.path.exists( path ):
        os.remove( path )
        assert not os.path.exists( path ), path

def get_file_length( path, default_length=0 ):
    try:
        return os.path.getsize( path )
    except OSError:
        return default_length

def to_ascii_string( string ):
    if type( string ) == unicode:
        return string.encode( 'ascii', 'replace' )
    else:
        return re.sub(r'[^\x20-\x7e]', '?', string )

def to_safe_path( path ):
    # this used to do more, but could never be right all the time.
    p = os.path.normpath( path )

def filename_to_safelength_path( filename ):
    part_length = 255
    if (not filename) or (len(filename) < part_length):
        return filename
    else:
        return os.path.join( *[filename[i:i+part_length] for i in range(0, len(filename), part_length)] )

def make_safelength_path( path ):
    path = os.path.normpath( path )
    (d,f) = os.path.split( path )
    return os.path.join( d, filename_to_safelength_path(f) )

def is_executable( path ):
    path = os.path.normpath( path )
    import stat
    return (os.stat( path ).st_mode) & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH) != 0

def validate_checksum_length( croot, checksum, length ):
    p = get_data_path( croot, checksum, length )
    real_length = get_file_length( p )
    if real_length != length:
	sys.stderr.write( "length mismatch %s != %s for %s\n" % ( real_length, length, p ) )
        return False
    md5 = calculate_checksum( p )
    if md5 != checksum:
	sys.stderr.write( "checksum mismatch %s != %s for %s\n" % ( md5, checksum, p ) )
        return False
    return True

def has_base( base, path ):
    base = os.path.normpath( base )
    path = os.path.normpath( path )
    common = os.path.commonprefix( [base, path] )
    return common == base

def ensure_path( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        os.makedirs( path )
    assert os.path.exists( path )

def ensure_parent_path( path ):
    path = os.path.normpath( path )
    pdir = os.path.dirname( path )
    ensure_path( pdir )

def get_extension( path ):
    ext = None
    if path:
        # i so completely and utterly hate python.
        parts = os.path.splitext( os.path.normpath( path ) )
        if len(parts) > 1 and parts[1] == '' and parts[0] != '.' and parts[0] != '..' and parts[0].strip() != '':
            ext = parts[0]
        if len(parts) > 1 and parts[1] != '':
            ext = parts[1]
    if ext != None:
        ext = ext.lower()
        ext = ext.lstrip('.')
    return ext

def smells_like_web_image( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    noext = os.path.splitext(path)[0]
    return path.endswith(WEB_MODIFIER)

def smells_like_canonical( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    if smells_like_any_metadata( path ):
        return False
    checksum = get_checksum_from_path( path )
    length = get_length_from_path( path )
    return checksum != None and length != None

def smells_like_browse( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    with open( path ) as f:
        for line in f:
            c = re.search( r'psync-o-pathics.com/canonical', line ) != None
            b = re.search( r'psync-o-pathics.com/browse', line ) != None
            t = re.search( r'<!-- mark -->', line ) != None
            if c or b or t:
               return True
    return False

def smells_like_any_metadata( path ):
    return _smells_like_metadata_exts( path, [metadata.PICKLE_DOTEXT, metadata.JSON_DOTEXT] )

def smells_like_pickled_metadata( path ):
    return _smells_like_metadata_exts( path, [metadata.PICKLE_DOTEXT] )

def smells_like_json_metadata( path ):
    return _smells_like_metadata_exts( path, [metadata.JSON_DOTEXT] )

def _smells_like_metadata_exts( path, exts ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    return reduce( lambda r,e: r or path.endswith(e), exts, False )

def smells_like_raw( path ):
    path = os.path.normpath( path )
    if not os.path.exists( path ):
        return False
    if smells_like_web_image( path ):
        return False
    ext = util.get_extension( path )
    return any(map(lambda raw_ext: raw_ext == ext, gRawExts))

def data_to_pickled_metadata_path( data_path ):
    path = os.path.normpath( data_path )
    return path + metadata.PICKLE_DOTEXT

def data_to_json_metadata_path( data_path ):
    path = os.path.normpath( data_path )
    return path + metadata.JSON_DOTEXT

def metadata_to_data_path( metadata_path ):
    path = os.path.normpath( metadata_path )
    path = re.sub( "\\"+metadata.PICKLE_DOTEXT+"$", "", path )
    path = re.sub( "\\"+metadata.JSON_DOTEXT+"$", "", path )
    return path

def extract_parent_path_mids( orig_path ):
    mids = None
    path = os.path.normpath( orig_path )
    path = os.path.dirname( path )
    parts = path.split( os.path.sep )
    if len(parts) >= 16:
        # trailing slash (?)
        if parts[-1] == '':
            parts = parts[:-1]
        mids = parts[-16:]
        ok = reduce((lambda a,b: a and len(b)==2), mids, True)
        if not ok:
            sys.stderr.write('bad mids %s -> %s (%s)\n' % (orig_path, mids, len(mids)))
            mids = None
    return mids

def get_data_path_mids( checksum ):
    mids = []
    for i in range( 0, len(checksum), gChecksumSplitLength ):
        mids.append( checksum[ i : i+gChecksumSplitLength ] )
        #sys.stdout.write( "get_data_path_mids(): %s\n" % " \\ ".join( mids ) )
    if mids == None:
        return None
    else:
        return os.path.join( *mids )

def get_data_parent_path( croot, checksum ):
    #sys.stdout.write( "get_data_parent_path( %s, %s )\n" % ( croot, checksum ) )
    path_mids = get_data_path_mids( checksum )
    p = os.path.join(
        croot,
        path_mids
        )
    #sys.stdout.write( "get_data_parent_path(): %s\n" % p )
    return p

def get_data_path( croot, checksum, length ):
    parent_path = get_data_parent_path( croot, checksum )
    dp = os.path.normpath( os.path.join( parent_path, "%s_%s" % ( checksum, length ) ) )
    #sys.stdout.write( "get_data_path( %s, %s, %s ): %s\n" % ( croot, checksum, length, dp ) )
    return dp

def get_pickled_metadata_path( croot, checksum, length ):
    return get_data_path( croot, checksum, length ) + metadata.PICKLE_DOTEXT

def get_json_metadata_path( croot, checksum, length ):
    return get_data_path( croot, checksum, length ) + metadata.JSON_DOTEXT

def get_dir_data_path( croot, hostname, dirpath_parts ):
    dir_data_parts = [ croot, "dirs", hostname ]
    parts.extend( dirpath_parts )
    dir_data_path = os.path.normpath( os.path.join( dir_data_parts ) )
    ensure_path( dir_data_path )
    return dir_data_path

def get_basename_from_path( path ):
    path = os.path.normpath( path )
    return os.path.basename( path )

def get_checksum_from_path( path ):
    path = os.path.normpath( path )
    parts = os.path.basename( path ).split( "_" )
    if len(parts) != 2 or len(parts[0]) != 32:
        return None
    else:
        return parts[0]

def get_length_from_path( path ):
    path = os.path.normpath( path )
    parts = os.path.basename( path ).split( "_" )
    if len(parts) != 2:
        return None 
    else:
        # [0] to remove metadata extensions.
        return parts[1].split(".")[0]

def get_checksum_length_from_path( path ):
    path = os.path.normpath( path )
    return get_checksum_from_path( path ), get_length_from_path( path )

def calculate_checksum( filepath ):
    try:
        filepath = os.path.normpath( filepath )
        m = csm.md5()
        f = open( filepath, "rb" )
        for chunk in iter( lambda: f.read(8192), "" ):
            m.update( chunk )
        return m.hexdigest()
    except Exception as e:
        sys.stderr.write( 'calculate_checksum(): failed for %s\n' % filepath )
        sys.stderr.write( '%s\n' % str(e) )
        sys.stderr.write( '-----> !!!??? HINT: ARE YOU SUDO ???!!!\n' )
        return None

def get_now_seconds():
    now_tt = get_now_timestruct()
    now_s = calendar.timegm( now_tt )
    return now_s

def get_now_timestruct():
    return time.gmtime()

def get_file_oldest_seconds( filepath ):
    filepath = os.path.normpath( filepath )
    nowt = get_now_timestruct()
    def to_safe_t( s ):
        if s == None or s <= 0:
            t = nowt
        else:
            t = time.gmtime( s )
        return t
    mt = to_safe_t( os.path.getmtime(filepath) )
    ct = to_safe_t( os.path.getctime(filepath) )
    mint = min( mt, ct )
    return calendar.timegm( mint )

def unhexlify_parts( parts ):
    return map( lambda e: binascii.unhexlify(e), parts )

def dict_select_by_keys( dict, *keys ):
    d2 = {}
    for k in keys:
        if k in dict:
            d2[k] = dict[k]
    return d2

def dict_select_by_fn( dict, matchfn ):
    d2 = {}
    for k in dict:
        if matchfn(k):
            d2[k] = dict[k]
    return d2

def dict_diff( a, b, out=[] ):
    all_keys = set(a.keys() + b.keys())
    for k in all_keys:
        missing = (not k in a) or (not k in b)
        if missing:
            out.append(k)
        else:
            av = a[k]
            bv = b[k]
            if type(av) != type(bv):
                out.append(k)
            elif type(av) == dict:
                dict_diff( av, bv, out )
            elif av != bv:
                out.append(k)
    return out

def to_named_size( length, precision=2 ):
    try:
        length = float(length)
        abbrevs = (
            (1<<50L, 'PB'),
            (1<<40L, 'TB'),
            (1<<30L, 'GB'),
            (1<<20L, 'MB'),
            (1<<10L, 'kB'),
            (1, 'bytes')
            )
        if length == 1:
            return '1 byte'
        for factor, suffix in abbrevs:
            if length >= factor:
                break
        s = '%.*f %s' % (precision, float(length) / float(factor), suffix)
        return s
    except Exception:
        return "Unknown"

def write_replace(path, data, backup=False):
    # 'transactional'ish.
    path_tmp = "%s_tmp" % path
    file_tmp = open( path_tmp, "w" )
    assert file_tmp != None, path # eh, IOError shoulda happened, anyway.
    file_tmp.write( data )
    file_tmp.flush()
    os.fdatasync( file_tmp )
    file_tmp.close()
    if backup and os.path.exists( path ):
        # yes, leaving LOTS of backup turds, in case it can ever help with recovery.
        # i guess this could kill me if it uses up too many inodes.
        path_bak = "%s.%s" % (path, str(int(time.time()*1000)))
        shutil.move( path, path_bak )
    shutil.move( path_tmp, path )
    assert os.path.exists( path ), path
    assert not os.path.exists( path_tmp ), path_tmp
    log( "write_replace: wrote %s\n" % path )

def test_is_executable():
    assert is_executable( sys.argv[0] )
    assert not is_executable( "TODO" )
    assert is_executable( "./client.py" )

def test_eat_arg():

    v0 = ['test']
    p = eat_arg( v0, 'test' )
    assert p == None

    v0a = ['test']
    p = eat_arg( v0a, 'test', nodash=True )
    assert p

    v0b = ['-test']
    p = eat_arg( v0b, 'test' )
    assert p

    v0b = ['--test']
    p = eat_arg( v0b, 'test' )
    assert p

    v1 = [1,2,3]
    p = eat_arg( v1, 'x' )
    assert p == None

    v2 = ['1','-2','3']
    p = eat_arg( v2, 2 )
    assert p

    v3 = ['1','--2','3']
    p = eat_arg( v3, 2 )
    assert p

    v3 = ['1','--2','bar','3']
    p = eat_arg( v3, 2, reqval=True )
    assert p == 'bar'

    v4 = ['1','--2','bar','3']
    p = eat_arg( v4, 2, reqval=True, remove=True )
    assert p == 'bar'
    assert v4 == ['1', '3']

def test_has_base():
    assert has_base( "a/b/c", "a/b/c/d" )
    assert not has_base( "a/b", "x/a/b" )
    assert has_base( "/mnt/pybak", "/mnt/pybak/browse" )

def test_uniq():
    l = ['abc', 'def', 'abc', 'ghi']
    u = uniq( l )
    assert len(u) == 3

def test_get_extension():
    assert None == get_extension( None )
    assert None == get_extension( "" )
    assert None == get_extension( " " )
    assert None == get_extension( "." )
    assert "foo" == get_extension( ".foo" )
    assert "foo" == get_extension( ".FOO" )
    assert "foo" == get_extension( ".bar.FOO" )

def test_metadata_to_data_path():
    assert metadata_to_data_path( "foo/bar/baz.metadata" ) == "foo/bar/baz"
    assert metadata_to_data_path( "foo/bar/bazmetadata" ) == "foo/bar/bazmetadata"

def test_dict_diff():
    out = dict_diff( {}, {}, [] )
    assert out == [], out
    #
    out = dict_diff( {1:1}, {}, [] )
    assert out == [1], out
    out = dict_diff( {}, {1:1}, [] )
    assert out == [1], out
    #
    out = dict_diff( {1:1}, {1:2}, [] )
    assert out == [1], out
    #
    out = dict_diff( {1:{2:3}}, {1:{2:4}}, [] )
    assert out == [2], out

def test_mids():
    assert     extract_parent_path_mids("/root/01/02/03/04/05/06/07/08/09/0a/0b/0c/0d/0e/somefile") == None
    assert     extract_parent_path_mids("/root/01/02/03/04/05/06/07/08/09/0a/0b/0c/0d/0e/0f/somefile") == None
    assert     extract_parent_path_mids("/root/01/02/03/04/05/06/07/08/09/0a/0b/0c/0d/0e/0f/16") == None
    assert     extract_parent_path_mids("/root/01/02/03/04/05/06/07/08/09/0a/0b/0c/0d/0e/0f/16/somefile") != None
    assert len(extract_parent_path_mids("/root/01/02/03/04/05/06/07/08/09/0a/0b/0c/0d/0e/0f/16/somefile")) == 16

def test():
    test_mids()
    test_has_base()
    test_is_executable()
    test_eat_arg()
    test_uniq()
    test_get_extension()
    test_metadata_to_data_path()
    test_dict_diff()

if __name__ == '__main__':
    import sys
    if eat_arg( sys.argv, "test" ):
	test()
    else:
        sys.stdout.write( "ERROR:\n usage: %s --test\n" % sys.argv[0] )
