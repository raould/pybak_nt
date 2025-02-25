#!/bin/env python

import io
import StringIO
import sys
import re
import os
import os.path
import util
import metadata
import traceback
import Image
import ImageDraw
import ImageFont
import font
import util
import metadata
import pgsqlutil as pgu
#import pg8000
#from pg8000 import DBAPI as db
import psycopg2 as db

g_font = font.get_font()

import logging
gLogger = logging.getLogger("thumber")
assert not gLogger == None
hdlr = logging.FileHandler("/tmp/thumber.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
gLogger.addHandler(hdlr)
gLogger.setLevel(logging.INFO)

def log_error( msg, stack=False ):
    m = str(msg)
    if stack:
        s = ">".join( util.extract_callers() )
        m = "ERROR [%s] %s" % ( s, msg )
    sys.stderr.write( m )
    gLogger.error( m )

def log( msg, caller=True ):
    m = str(msg)
    if caller:
        c = util.extract_callers()[-1]
        m = "[%s] %s" % ( c, msg )
    sys.stdout.write( m )
    gLogger.info( m )

def generate_thumbnail( path, thumb_buf ):
    try:
        i = Image.open( path )
        i.thumbnail( (128, 128) )
        i = i.convert( 'RGB' )
        if "." in path:
            ext = path.split(".")[-1]
            draw = ImageDraw.Draw( i )
            (tw,th) = draw.textsize( ext, font=g_font )
            (iw,ih) = i.size
            tx = iw - tw - 5
            ty = ih - th - 5
            draw.rectangle( (tx,ty,tx+tw+5,ty+th+5), fill="black" )
            draw.text( (tx+1,ty+1), ext, fill="white", font=g_font )
        i.save( thumb_buf, "JPEG" )
        return True
    except:
        ex = sys.exc_info()
        if (not ("cannot identify" in str(ex[1]))):
            log( "[buildhtml] path = %s, ex = %s, %s\n" % (path, ex, traceback.format_exception(*ex)) )
        return False

def db_insert_thumbnail( dbconn, cnameid, jpeg_buf ):
    jpeg_bytes = jpeg_buf.getvalue()
    jpeg_db = pg8000.Binary( jpeg_bytes )
    thumb_kvps = [('cnameid',cnameid),('jpeg',jpeg_db)]
    thumb_cols = pgu.cols_str( thumb_kvps )
    thumb_values_parameters = pgu.values_parameters_str( thumb_kvps )
    thumb_sql = "insert into thumbnail " + thumb_cols + " values " + thumb_values_parameters
    dbcur = dbconn.cursor()
    thumb_values_data = pgu.values_parameters_list( thumb_kvps )
    thumb_ids = pgu.db_insert_returning_ids( dbcur, thumb_sql, thumb_values_data )
    assert len(thumb_ids) == 1, str([cnameid, thumb_ids])
    dbconn.commit()
    dbcur.close()

def db_insert_null_thumbnail( dbconn, cnameid ):
    dbcur = dbconn.cursor()
    thumb_ids = pgu.db_insert_returning_ids( dbcur, "insert into thumbnail (cnameid, jpeg) values (%s, null)", [cnameid] )
    assert len(thumb_ids) == 1, str(cnameid)
    dbconn.commit()
    dbcur.close()

def is_thumbnail_needed( dbconn, cnameid ):
    dbcur = dbconn.cursor()
    pgu.dbexe( dbcur, "select count(*) from thumbnail where cnameid = %s", [cnameid] )
    rows = dbcur.fetchall()
    assert len(rows) == 1
    assert len(rows[0]) == 1
    needed = (rows[0][0] == 0)
    dbcur.close()
    return needed

def get_exts( dbconn, cnameid ):
    dbcur = dbconn.cursor()
    pgu.dbexe( dbcur, "select extension.extension from extension, cnameid_x_extensionid where extension.id = cnameid_x_extensionid.extensionid and cnameid_x_extensionid.cnameid = %s" % cnameid )
    exts = dbcur.fetchall()
    dbcur.close()
    return exts

def get_canonical_path( dbconn, cnameid, canonical_root ):
    dbcur = dbconn.cursor()
    pgu.dbexe( dbcur, "select sum, len from cname where id = %s", [cnameid] )
    row = dbcur.fetchone()
    dbcur.close()
    checksum = str(row[0]).replace( '-', '' ) # god, i freaking hate postgres.
    length = str(row[1])
    return util.get_data_path( canonical_root, checksum, length )

def thumbize_single( dbconn, cnameid, canonical_root ):
    canonical_path = get_canonical_path( dbconn, cnameid, canonical_root )
    exts = get_exts( dbconn, cnameid )
    assert canonical_path, str(cnameid)
    if not os.path.exists( canonical_path ):
        log_error( "MISSING ORIGINAL FILE: %s %s\n" % ( str(exts), canonical_path ) ) 
        mdj_path = "%s.%s" % ( canonical_path, metadata.JSON_DOTEXT )
        if os.path.exists( mdj_path ):
            md = metadata.read_json_path( mdj_path )
            log_error( "METADATA FOR MISSING ORIGINAL: %s\n" % md )
        return False
    needed = is_thumbnail_needed( dbconn, cnameid )
    log( "cnameid = %s, exts = %s, needed = %s\n" % ( cnameid, str(exts), needed ) )
    if needed:
        thumb_buf = StringIO.StringIO()
        generated = generate_thumbnail( canonical_path, thumb_buf )
        log( "generated = %s\n" % generated )
        if generated:
            db_insert_thumbnail( dbconn, cnameid, thumb_buf )
        else:
            db_insert_null_thumbnail( dbconn, cnameid )
    return True

# todo: see if this really works with StringIO.
def get_thumbnail_jpeg( dbconn, cnameid, dst_io ):
    dbcur = dbconn.cursor()
    pgu.dbexe( dbcur, "select jpeg from thumbnail where cnameid = %s", [cnameid] )
    row = dbcur.fetchone()
    dst_io.write( str(row[0]) )
    dbcur.close()

def sanity_check_write_thumbnail( dbconn, cnameid ):
    dst_io = open( "/tmp/thumb.jpg", "wb" )
    get_thumbnail_jpeg( dbconn, cnameid, dst_io )
    dst_io.close()

def thumbize( dbconn, canonical_root ):
    done = False
    offset = 0
    step = 100
    while not done:
        dbcur = dbconn.cursor()
        pgu.dbexe( dbcur, "select id from cname limit %s offset %s", [step, offset] )
        offset += step
        all_cname_ids = dbcur.fetchall()
        dbcur.close()
        if all_cname_ids == None or len(all_cname_ids) == 0:
            done = True
        else:
            for cnameid_wrapper in all_cname_ids:
                assert len(cnameid_wrapper) == 1, str(cnameid_wrapper)
                cnameid = cnameid_wrapper[0]
                log( ">>> starting %s\n" % cnameid )
                thumbize_single( dbconn, cnameid, canonical_root )

def usage(msg=None):
    if msg:
        log_error("[%s]\n" % msg)
    log_error( "usage: %s <canonical_root>\n" % sys.argv[0] )
    sys.exit(1)

if __name__ == '__main__':
    try:
        canonical_root = os.path.abspath( sys.argv[1] )
        if not canonical_root:
            usage()
        log( "canonical_root = %s\n" % canonical_root )
        dbconn = db.connect( host="localhost", user="pybak", password="kabyp", database="pybakdb" )
        thumbize( dbconn, canonical_root )
    except Exception, e:
        usage( msg=traceback.format_exc(e) )
    finally:
        if dbconn:
            dbconn.close()
    
