#!/usr/bin/python

# warning: there's a lot of convention going on here! see psql.schema.

import sys
import os
import os.path
import util
import visit_core
import traceback
import pgsqlutil as pu
#from pg8000 import DBAPI as db
import psycopg2 as db

def upsert_parent_of_root( dbcur, hostid ):
    return upsert_path( dbcur, hostid, '' )

def upsert_path( dbcur, hostid, path ):
    pu.logn( "upsert_path", hostid, path )
    bhpid = pu.upsert_single_retid( dbcur, "b_path", [('path',path)] )
    bhpdid = pu.upsert_single_retid( dbcur, "b_hostPath", [('hostid',hostid),('b_pathid',bhpid)] )
    pu.logn( "upsert_path", hostid, path, bhpid, bhpdid )
    return bhpdid

def upsert_parents_subs( dbcur, hostid, subs, parentofrootid ):
    parentid = parentofrootid
    for i in range(len(subs)):
        pathid = upsert_path( dbcur, hostid, subs[i] )
        pu.logn( "upsert_parent_subs", pathid, parentid )
        pu.upsert_single_noret( dbcur, "b_hostPathDir", [('parentid',parentid),('pathid',pathid)] )
        parentid = pathid
    return parentid

def upsert_file( dbcur, name, parentid ):
    nameid = pu.upsert_single_retid( dbcur, "b_fileName", [('name',name)] )
    pu.upsert_single_noret( dbcur, "b_hostPathFile", [('parentid',parentid),('nameid',nameid)] )

def denormalize_item( dbcur, hdi_row ):
    subs = util.path_to_subpaths( hdi_row['parent_path'] )
    # assertions to make sure things are good, including parentid likely being valid below.
    assert len(subs) > 0
    assert subs[0] == "/"
    parentofrootid = upsert_parent_of_root( dbcur, hdi_row['hostid'] )
    parentid = upsert_parents_subs( dbcur, hdi_row['hostid'], subs, parentofrootid )
    upsert_file( dbcur, hdi_row['item_name'], parentid )
    
def visit_normalized_items( dbconn, denorm_fn ):
    sql = "select * from hostDirItem order by id"
    dbcur = dbconn.cursor()
    pu.dbexe( dbcur, sql )
    def iterfn( row ):
        host = pu.fetch_one( dbconn.cursor(), "select host from host where id = %s" % row[1] )[0]
        parent_path = pu.fetch_one( dbconn.cursor(), "select dirPath from dir where id = %s" % row[2] )[0]
        item_name = pu.fetch_one( dbconn.cursor(), "select name from dirItemName where id = %s" % row[3] )[0]
        hdi = { 'id':row[0],
                'hostid':row[1],
                'host':host,
                'dirid':row[2],
                'parent_path':parent_path,
                'dirItemNameid':row[3],
                'item_name':item_name }
        pu.logn( "hdi = %s" % hdi )
        denorm_fn( dbconn.cursor(), hdi )
    pu.chunked_row_iter( dbcur, iterfn, 100 )

def upsert_db_all():
    dbconn = db.connect( host="192.168.123.65", user="pybak", password="kabyp", database="pybakdb" )
    visit_normalized_items( dbconn, denormalize_item )
    dbconn.commit()
    dbconn.close()

if __name__ == '__main__':
    upsert_db_all()
