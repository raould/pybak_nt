import sys
import re
#from pg8000 import DBAPI as db
import psycopg2 as db

gLog = True

def logn( *args ):
    if gLog:
        for a in args:
            sys.stdout.write( str([to_utf8str_unescaped(a), type(a)]) )
        sys.stdout.write( "\n" )

def escape_quotes( string, single_quote ):
    return string.replace( single_quote, single_quote+single_quote )

def escape( sql ):
    sql = sql.replace( "%", "%%" )
    # i think we're always using only single quotes.
    if len(sql) > 2:
        if sql[0]=="'" and sql[-1]=="'":
            contents = sql[1:-1]
            ce = escape_quotes( contents, "'" )
            sql = "'" + ce + "'"
        elif sql[0]=='"' and sql[-1]=='"':
            assert False, sql
        else:
            sql = escape_quotes( sql, "'" )
    elif "'" in sql:
        assert False, sql
    return sql

def to_utf8str_unescaped( data ):
    if data == None:
        return None
    if isinstance( data, basestring ):
        if isinstance( data, unicode ):
            return data.encode( 'utf-8' )
        else:
            return data
    else:
        return str(data)

def to_utf8str( data ):
    def core( _data ):
        _ustr = to_utf8str_unescaped( _data )
        if _ustr == None:
            return None
        else:
            return escape(_ustr)
    ustr = core( data )
    logn( data, " -> ", ustr )
    return ustr

def where_str( kvps ):
    def mapfn( p ):
        col = to_utf8str(p[0])
        val = to_utf8str(p[1])
        if val == None:
            p2 = col + " is null"
        else:
            p2 = col + "='" + val + "'"
        return p2
    c = map( mapfn, kvps )
    where = " and ".join( c )
    logn( "where", where )
    return where

def cols_str( kvps ):
    def mapfn( p ):
        pu = to_utf8str(p[0])
        logn( p[0], " -->> ", pu )
        return pu
    c = map( mapfn, kvps )
    cols = "(" + ",".join( c ) + ")"
    logn( "cols", cols )
    return cols

def values_str( kvps ):
    def mapfn( p ):
        pu = to_utf8str(p[1])
        po = "'" + pu + "'"
        return po
    c = map( mapfn, kvps ) 
    values = "(" + ",".join( c ) + ")"
    logn( "values", values )
    return values

def values_parameters_str( kvps ):
    def mapfn( p ):
        pu = to_utf8str(p)
        return pu
    c = map( mapfn, kvps )
    vps = "(" + ",".join( c ) + ")"
    logn( "vps", vps )
    return vps

def values_parameters_list( kvps ):
    vpl = map( lambda t:t[1], kvps )
    logn( "vpl", vpl )
    return vpl

def dbexe( dbcur, sql, args=() ):
    # trying to fix handling mac os x metadata paths.
    sql = unicode( sql, 'utf-8' )
    logn( "dbexe: %s #%s" % ( sql, len(args) ) )
    dbcur.execute( sql, args )
    # caller decides if they want to fetch() anything.
    return None

def db_insert_returning_ids( dbcur, sql, args=() ):
    ids = []
    sql = sql.rstrip()
    sql = re.sub( ";$", "", sql )
    sql = sql + " returning id;"
    # trying to fix handling mac os x metadata paths.
    sql = unicode( sql, 'utf-8' )
    logn( "db_insert_returning_ids: %s #%s" % ( sql, len(args) ) )
    dbcur.execute( sql, args )
    for row in dbcur:
        ids.append( row[0] )
    return ids

def id_sql( table, kvps ):
    where = where_str( kvps )
    sql = "select id from " + table + " where " + where
    return sql

def row_sql( table, kvps, selected_cols=["*"] ):
    where = where_str( kvps )
    sql = "select " + ",".join( selected_cols ) + " from " + table + " where " + where
    return sql

def fetch_row( dbcur, table, kvps ):
    sql = row_sql( table, kvps )
    assert 'select' in sql.lower()
    return fetch_one( dbcur, sql )

def fetch_one( dbcur, sql ):
    assert 'select' in sql.lower()
    dbexe( dbcur, sql )
    r1 = dbcur.fetchone()
    return r1 if r1 != None else None

def fetch_all( dbcur, sql ):
    assert 'select' in sql.lower()
    ret = None
    dbexe( dbcur, sql )
    all = dbcur.fetchall()
    if all != None:
        ret = []
        col_names = [ d[0] for d in dbcur.description ]
        for row in all:
            ret.append( dict(zip(col_names, row)) )
    logn( "fetch_all: #%s" % str(0) if ret==None else str(len(ret)) )
    return ret

def fetch_id( dbcur, sql ):
    assert 'select' in sql.lower()
    r1 = fetch_one( dbcur, sql )
    logn( "fetch_id: %s" % r1 )
    return r1[0] if r1 != None else None

# def upsert_single_by_id( dbcur, table, kvps ):
#     s = _upsert_single_by_id( dbcur, table, kvps )
#     logn( "upsert_single_by_id: s = %s" % s )
#     return s
# def _upsert_single_by_id( dbcur, table, kvps ):
#     rid = None
#     sql = id_sql( table, kvps )
#     oldv = fetch_id( dbcur, sql )
#     if oldv == None:
#         cols = cols_str( kvps )
#         values = values_str( kvps )
#         sql = "insert into " + table + " " + cols + " values " + values + " returning id"
#         dbexe( dbcur, sql )
#         return dbcur.fetchone()[0]
#     else:
#         return oldv

def upsert_single_retid( dbcur, table, kvps ):
    s = _upsert_single_retid( dbcur, table, kvps )
    logn( "upsert_single_retid: s = %s" % s )
    return s
def _upsert_single_retid( dbcur, table, kvps ):
    oldv = fetch_row( dbcur, table, kvps )
    if oldv == None:
        cols = cols_str( kvps )
        values = values_str( kvps )
        sql = "insert into " + table + " " + cols + " values " + values + " returning id"
        dbexe( dbcur, sql )
        r = dbcur.fetchone()[0]
        logn( "_upsert_single_retid: r = ", r )
        return r
    else:
        logn( "_upsert_single_retid: r =", oldv )
        return oldv[0]

def upsert_single_noret( dbcur, table, kvps ):
    oldv = fetch_row( dbcur, table, kvps )
    if oldv == None:
        cols = cols_str( kvps )
        values = values_str( kvps )
        sql = "insert into " + table + " " + cols + " values " + values
        dbexe( dbcur, sql )

def chunked_row_iter( cursor, iterfn, stepsize=1000 ):
    logn( "chunked_row_iter: stepsize = ", stepsize )
    results = cursor.fetchmany( stepsize )
    while results:
        logn( "chunked_row_iter: more results..." )
        for row in results:
            iterfn( row )
        logn( "chunked_row_iter: ...more results" )
        results = cursor.fetchmany( stepsize )
    logn( "chunked_row_iter: done" )
