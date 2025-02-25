#!/usr/bin/env python

import sys
import os
import os.path
import client
import service
import server
import util
import itest_config as itc
import shutil
import thread

def setup( prewrite=None ):
    sys.stdout.write( "[itest_full] setup( %s )\n" % prewrite )

    shutil.rmtree( os.path.join( itc.basedir, itc.baksubdir ), True )
    shutil.rmtree( os.path.join( itc.basedir, itc.htmlsubdir ), True )

    serverd = server.Server( itc.basedir, itc.baksubdir )
    if prewrite:
        prewrite_file( prewrite )

    httpd = service.make_service( itc.port, serverd )
    thread.start_new_thread( httpd.serve_forever, () )

    c = client.Client( itc.clienthost )
    return httpd, c;

def prewrite_file( sourcepath ):
    sys.stdout.write( "[itest_full] prewrite_file( %s )\n" % ( sourcepath ) )
    checksum = util.calculate_checksum( sourcepath )
    length = os.path.getsize( sourcepath )
    dst = util.get_data_path( os.path.join( itc.basedir, itc.baksubdir ), checksum, length )
    util.ensure_parent_path( dst )
    shutil.copyfile( sourcepath, dst )

#

def with_http_server( fn, prewrite ):
    sys.stdout.write( "[itest_full]: with_http_server( %s, %s ): ...\n" % ( fn, prewrite ) )
    httpd, c = setup( prewrite=prewrite )
    sys.stdout.write( "[itest_full]: with_http_server(): fn( %s, %s )\n" % ( httpd, c ) )
    try:
        fn( httpd, c )
    except SystemExit, sex:
        pass
    sys.stdout.write( "[itest_full]: ...with_http_server.\n" )

def swap_prewrite( prewrite, path ):
    if prewrite:
        return path
    else:
        return None

#

def match( prewrite ):
    with_http_server( match_core, swap_prewrite( prewrite, itc.path ) )
def match_core( httpd, c ):
    sys.stdout.write( "[itest_full]: match()\n" )
    length = c.get_remote_length( "0.0.0.0", itc.port, itc.path, itc.checksum, itc.length )
    sys.stdout.write( "[itest_full] match(): length = %s\n" % length )
    if prewrite:
        assert length == itc.length, "expected it to already exist."
    else:
        assert length == 0, "expected it to be new."

def save_image( prewrite ):
    with_http_server( save_image_core, swap_prewrite( prewrite, "itest_data_image.gif" ) )
def save_image_core( httpd, c ):
    sys.stdout.write( "[itest_full]: save_image()\n" )
    saved = c.save_file( "0.0.0.0", itc.port, "itest_data_img.gif" )
    sys.stdout.write( "[itest_full] save_image(): saved = %s\n" % saved )

    dp = os.path.join( itc.basedir, itc.baksubdir, "ca", "09", "71", "33", "f9", "83", "02", "f6", "3d", "f8", "bc", "6e", "69", "6e", "b4", "13", "ca097133f98302f63df8bc6e696eb413_281" )
    assert os.path.exists( dp ), dp
    assert os.path.getsize( dp ) == 281

    tdp = os.path.join( itc.basedir, itc.htmlsubdir, ".thumbs", "ca", "09", "71", "33", "f9", "83", "02", "f6", "3d", "f8", "bc", "6e", "69", "6e", "b4", "13", "ca097133f98302f63df8bc6e696eb413_281_thumb.jpg" )
    assert os.path.exists( tdp ), tdp
    assert os.path.getsize( tdp ) == 1005

    sheetp = os.path.join( itc.basedir, itc.htmlsubdir, itc.clienthost, os.environ['PWD'][1:], "000_thumbnails.html" )
    sheetf = open( sheetp, 'r' )
    sheet = sheetf.read()
    expected = 'img src="%s"' % os.path.join( itc.urlize, itc.htmlsubdir, ".thumbs", "ca", "09", "71", "33", "f9", "83", "02", "f6", "3d", "f8", "bc", "6e", "69", "6e", "b4", "13", "ca097133f98302f63df8bc6e696eb413_281_thumb.jpg" ).__str__()
    assert expected in sheet, `expected`+" in "+`sheet`

def save_small( prewrite ):
    with_http_server( save_small_core, swap_prewrite( prewrite, "itest_data_full" ) )
def save_small_core( httpd, c ):
    sys.stdout.write( "[itest_full]: save_small()\n" )
    saved = c.save_file( "0.0.0.0", itc.port, "itest_data_full" )
    sys.stdout.write( "[itest_full] save_small(): saved = %s\n" % saved )
    dp = os.path.join( itc.basedir, itc.baksubdir, "c0", "10", "af", "f9", "dc", "62", "76", "fd", "b7", "ef", "ef", "d1", "a2", "75", "76", "58", "c010aff9dc6276fdb7efefd1a2757658_8" )
    assert os.path.exists( dp ), dp
    assert os.path.getsize( dp ) == 8

def save_thrash( prewrite ):
    with_http_server( save_thrash_core, swap_prewrite( prewrite, itc.path ) )
def save_thrash_core( httpd, c ):
    sys.stdout.write( "[itest_full]: save_thrash()\n" )
    c.chunk_size = 1
    saved = c.save_file_offset( "0.0.0.0", itc.port, itc.path, itc.checksum, itc.length, 0 )
    sys.stdout.write( "[itest_full] save_thrash(): saved = %s\n" % saved )
    dp = os.path.join( itc.basedir, itc.baksubdir, "60", "79", "81", "15", "2d", "3f", "d0", "62", "e5", "a6", "a6", "94", "0c", "3e", "44", "76", "607981152d3fd062e5a6a6940c3e4476_140" )
    assert os.path.exists( dp ), dp
    assert os.path.getsize( dp ) == 140

def save_dir( prewrite ):
    if prewrite:
        raise Exception( "prewrite not supported for this command 'save_dir'" )
    with_http_server( save_dir_core, prewrite )
def save_dir_core( httpd, c ):
    sys.stdout.write( "[itest_full]: save_dir()\n" )
    saved = c.save_dir( "0.0.0.0", itc.port, itc.dirpath, False, 1, 0 )
    sys.stdout.write( "[itest_full] save_dir(): saved = %s\n" % saved )
    dp = os.path.join( itc.basedir, itc.baksubdir, "05", "ec", "d2", "3c", "c1", "d8", "a4", "e6", "5f", "c8", "04", "f3", "0c", "b8", "d5", "c4", "05ecd23cc1d8a4e65fc804f30cb8d5c4_1339" )
    assert os.path.exists( dp ), dp
    assert os.path.getsize( dp ) == 1339

def append( prewrite ):
    if prewrite:
        raise Exception( "prewrite not supported for this command 'append'" )
    with_http_server( append_core, prewrite )
def append_core( httpd, c ):
    sys.stdout.write( "[itest_full]: append()\n" )
    if os.path.exists( "itest_data_tmp" ):
        os.remove( "itest_data_tmp" )
    full_length = os.path.getsize( "itest_data_full" )
    full_checksum = util.calculate_checksum( "itest_data_full" )

    shutil.copyfile( "itest_data_part", "itest_data_tmp" )
    saved = c.save_file_offset( "0.0.0.0", itc.port, "itest_data_tmp", full_checksum, full_length, 0 )
    sys.stdout.write( "[itest_full] append(): saved = %s\n" % saved )
    assert saved

    part_len = c.get_remote_length( "0.0.0.0", itc.port, itc.path, full_checksum, full_length )
    sys.stdout.write( "[itest_full] part_len = %s\n" % part_len )
    assert part_len == os.path.getsize( "itest_data_part" )

    os.remove( "itest_data_tmp" )
    shutil.copyfile( "itest_data_full", "itest_data_tmp" )
    saved = c.save_file_offset( "0.0.0.0", itc.port, "itest_data_tmp", full_checksum, full_length, part_len )
    sys.stdout.write( "[itest_full] len = %s\n" % len )
    assert saved
    assert full_length == os.path.getsize( util.get_data_path( os.path.join(itc.basedir,itc.baksubdir), full_checksum, full_length ) )

if __name__ == '__main__':
    from sets import Set

    prewrite = 'prewrite' in sys.argv

    if 'match' in sys.argv:
        match( prewrite )
    elif 'save_image' in sys.argv:
        save_image( prewrite )
    elif 'save_small' in sys.argv:
        save_small( prewrite )
    elif 'save_thrash' in sys.argv:
        save_thrash( prewrite )
    elif 'save_dir' in sys.argv:
        save_dir( prewrite )
    elif 'append' in sys.argv:
        append( prewrite )
    else:
        print "ERROR usage: command?: " + " ".join( sys.argv )
