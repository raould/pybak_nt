#!/usr/bin/python

# lo, i hate python...
import sys
sys.setdefaultencoding( 'utf8' )
import site

# ...back to regular stuff.
import re
import os
import exts
import util
import metadata
import visit_core
import traceback
import calendar
import pgsqlutil
#from pg8000 import DBAPI as db
import psycopg2 as db

# do i hate sql? yes. yes, i do.
def upsert_single( dbcur, table, kvps ):
    rid = None
    r1 = fetchone_id( dbcur, table, kvps )
    visit_core.log( "r1 = %s %s\n" % ( r1, type(r1) ), True )
    if r1 == None:
        cols = cols_str( kvps )
        values = values_str( kvps )
        sql = "insert into " + table + " " + cols + " values " + values
        dbexe( dbcur, sql )
        rid = fetchone_id( dbcur, table, kvps )[0]
    else:
        r2 = dbcur.fetchone()
        if r2 != None:
            visit_core.log_error( "more than one entry for " + kvps + "\n" )
            return None
        rid = r1[0]
    if rid == None:
        raise Exception( "wtf? " + str(kvps) )
    return rid

def update_db( dbconn, dirpath, filename ):
    sys.stdout.write( "update_db: %s %s\n" % (dirpath, filename) )
    dz = dirpath.split( os.sep )
    print dz

        # kvps = [('prefix',''),('depth',str(len(dirs)))]
        # cols = cols_str( kvps )
        # values = values_str( kvps )
        # sql = "insert into path_prefix " + cols + " values " + values
        # dbexe( dbcur, sql )

def to_utf8( data ):
    if isinstance( data, basestring ) and isinstance( data, unicode ):
        return data.encode( 'utf-8' )
    else:
        return data

def run():
    dbconn = db.connect( host="localhost", user="pybak", password="kabyp", database="pybakdb" )
    dbcur = dbconn.cursor()

    sql = "select path from hostpath"
    dbexe( dbcur, sql )

    # uh, pg8000 sucks with the warnings here. ignore them!?
    for row in dbcur:

        path = to_utf8( row[0] )
        if "\/" in path: # todo: this probably doesn't sufficiently cover all such possible evils!
            sys.stderr.write( "can't handle path with escaped slashes: [%s]\n" % path )
            continue
        if path[0] != "/":
            sys.stderr.write( "can't handle root-with-no-file: [%s]\n" % path )
            continue
        if len(path) <= 1:
            sys.stderr.write( "can't handle short path: [%s]\n" )
            continue

        # get path to parent dir - drop the file name.
        # save each next longer path into the db.
        # if the path is the final parent path, link it to the file name.
        filename = os.path.basename( path )
        dirpath = os.path.dirname( path )
        if len(filename) == 0:
            sys.stderr.write( "can't handle empty filename: [%s|%s]\n" % (filename, path) )
            continue
        if len(dirpath) == 0:
            sys.stderr.write( "can't handle empty dirpath: [%s|%s]\n" % (dirpath, path) )
            continue

        update_db( dbconn, dirpath, filename )
        sys.exit(1)

    dbconn.close();

if __name__ == '__main__':
    run()

