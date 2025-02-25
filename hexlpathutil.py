#!/usr/bin/env python

import sys
import os
import os.path
import binascii
import util
import visit_core

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# really kinda only works on the client side,
# as server side might use different os.sep.
# (i hate python.)
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# todo: test on non-ext file systems.

def log( msg ):
    sys.stdout.write( msg )

# this is a self-indicting hail-mary hack;
# trying to parse previously hexlified file names!?
def to_ascii_path( path ):
    return util.to_ascii_string(to_clear_path(path))

# this is a self-indicting hail-mary hack;
# trying to parse previously hexlified file names!?
def to_clear_path( path ):
    def can_unhexlify( p ):
        try:
            c = binascii.unhexlify( p )
            return True
        except TypeError, e:
            return False
    can = can_unhexlify( path )
    while can_unhexlify( path ):
        upath = binascii.unhexlify( path )
        if upath == path:
            break
        path = upath
    # if it was e.g. a linux path it could be non-unicode e.g. raw bytes.
    #log( "to_clear_path: %s %s '%s'\n" % (can, type(path), path))
    if type(path) == unicode:
        return path.encode("utf-8")
    else:
        return path

# this is a self-indicting hail-mary hack. :-(
def to_hexl_path( path ):
    try:
        # questionable hack, in case it was already hexlified! :-(
        c = to_clear_path( path ) # -> either unicode or python str.
        return binascii.hexlify( c ) # -> python str (bytes).
    except:
        return binascii.hexlify( path )

def hexl_path_to_hexl_list( hexl_path, clear_sep ):
    #log( "+ hexl_path_to_hexl_list: %s, %s\n" % (hexl_path, clear_sep) )
    clear = to_clear_path( hexl_path )
    plist = clear.split( clear_sep )
    # dunno why, but this is what i've been doing, apparently.
    while( len(plist) > 0 and plist[0] == clear_sep ):
        plist = plist[1:]
    xlist = map( lambda p: to_hexl_path(p), plist )
    visit_core.log()
    return xlist

def path_to_hexl_list( path ):
    #log( "+ path_to_hexl_list: %s\n" % path )
    l = map(lambda e:binascii.hexlify(e), path_to_list(path))
    #log( "- path_to_hexl_list: %s\n" % l )
    return l

def hexl_list_to_path( hexl_list ):
    return os.path.join( map(lambda e:binascii.unhexlify(e), hexl_list) )

# e.g. /a/b/c -> [a,b,c] where a,b are dirs, c is file.
def path_to_list( path ):
    #log( "+ %s\n" % path )
    l = _path_to_list( os.path.normpath( path ) )
    #log( "- %s\n" % l )
    return l

def _path_to_list( path ):
    d,f = os.path.split( path )
    if len(d) and len(f):
        p = _path_to_list( d )
        p.extend( [f] )
    elif len(f):
        p = [f]
    else:
        p = []
    return p

def test_to_clear_path_A():
    p = "/1"
    c = to_clear_path( p )
    assert "/1" == c, (p,c)

def test_to_clear_path_B():
    p = binascii.hexlify( "/1" )
    c = to_clear_path( p )
    assert "/1" == c, (p,c)

def test_to_clear_path_C():
    p = binascii.hexlify( binascii.hexlify("/1") )
    c = to_clear_path( p )
    assert "/1" == c, (p,c)

def test_to_clear_path_D():
    p = binascii.hexlify( binascii.hexlify( binascii.hexlify("/1") ) )
    c = to_clear_path( p )
    assert "/1" == c, (p,c)

def test_to_hexl_path():
    p = binascii.hexlify( binascii.hexlify( binascii.hexlify("/1") ) )
    h = to_hexl_path( p )
    assert binascii.hexlify("/1") == h, (p,h)

def mae( l, r ):
    if l != r:
        assert False, "%s != %s" % (l,r)

def test_path_to_list():
    mae( hexl_path_to_hexl_list( "2f612f62", "/" ), ["", "61","62"] )
    mae( path_to_hexl_list( "/" ), [] )
    mae( path_to_hexl_list( "/a" ), ["61"] )
    mae( path_to_hexl_list( "/a/b" ), ["61","62"] )
    mae( path_to_list( "/" ), [] )
    mae( path_to_list( "/a/b/c" ), ["a","b","c"] )
    mae( path_to_list( "/a1/b2/c3" ), ["a1","b2","c3"] )
    mae( path_to_list( "/a/../c" ), ["c"] )
    mae( path_to_list( "/../../c" ), ["c"] )
    mae( path_to_list( "" ), ["."] )
    mae( path_to_list( "//c/foo" ), ["c","foo"] )

def test():
    for tfn in [
        test_path_to_list,
        test_to_clear_path_A,
        test_to_clear_path_B,
        test_to_clear_path_C,
        test_to_clear_path_D,
        test_to_hexl_path,
        ]:
        print tfn
        tfn()
    print "tests passed"

if __name__ == '__main__':
    import sys
    if util.eat_arg( sys.argv, "test" ):
	test()
    else:
        sys.stderr.write( "ERROR:\n usage: %s --test\n" % sys.argv[0] )
