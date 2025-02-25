#!/usr/bin/env python

from mako.template import Template
#from pg8000 import DBAPI as db
import psycopg2 as db
import sys
import os
import os.path
import pgsqlutil
import urlparse

def assert_lens( a, b ):
    if len(a) != len(b):
        sys.stderr.write( "a = %s\n" % str(len(a)) )
        sys.stderr.write( "b = %s\n" % str(len(b)) )

class Data:
    def __init__( self, file_idXname, file_ids, filenames, cname_ids, cnames, cname_id2name ):
        self.file_idXname = file_idXname
        self.file_ids = file_ids
        self.filenames = filenames
        self.cname_ids = cname_ids
        self.cnames = cnames
        self.cname_id2name = cname_id2name

class DirWeb:

    def __init__( self, base_url, host, path, dbconn ):
        self.base_url = base_url
        self.host = host
        self.path = path
        self.dbconn = dbconn
        self.host_id = self.get_host_id() # todo: map string to id, from 'normalized' tables.
        self.d_dir_id = self.get_d_dir_id() # todo: map string to id, from 'denormalized' tables.

    def get_host_id( self ):
        return 3

    def get_d_dir_id( self ):
        return 217

    def get_dirs( self, data ):
        return self.get_dirs4template()

    def get_dirs4template( self ):
        # select all the items of type dir, sorted.
        # none of these are canonical files.
        # something vaguely like:
        # {a. get host id.}
        # {b. get this (parent of items) dir id.}
        # c. get dir type id.
        # todo: join to just get the names, in sorted order.
        # d. select.
        dbcur = self.dbconn.cursor()
        dir_type_id = pgsqlutil.fetch_id( dbcur, pgsqlutil.id_sql('d_dirItemType', [('type','directory')]) )
        sql = ' '.join( ['select d_dirItemName.name from d_dirItemName, d_hostDirItemType',
                         'where',
                         ' and '.join( ['d_hostDirItemType.d_dirItemNameid = d_dirItemName.id',
                                        'd_hostDirItemType.hostid = ' + str(self.host_id),
                                        'd_hostDirItemType.d_dirid = ' + str(self.d_dir_id),
                                        'd_hostDirItemType.d_dirItemTypeid = ' + str(dir_type_id) ] ),
                         'order by name asc'
                         ] )
        dirs = pgsqlutil.fetch_all( dbcur, sql )
        dbcur.close()
        return None if dirs == None else map(lambda t:t['name'], dirs)

    def get_file_idXnames( self ):
        # 2. select all the items of type file, sorted.
        # these are all canonical files.
        # something vaguely like:
        # {a. get host id.}
        # {b. get this (parent of items) dir id.}
        # c. get file type id.
        dbcur = self.dbconn.cursor()
        file_type_id = pgsqlutil.fetch_id( dbcur, pgsqlutil.id_sql('d_dirItemType', [('type','file')]) )
        sql = ' '.join( ['select d_hostDirItemType.id, d_dirItemName.name',
                         'from d_hostDirItemType, d_dirItemName',
                         'where',
                         ' and '.join( ['d_hostDirItemType.d_dirItemNameid = d_dirItemName.id',
                                        'd_hostDirItemType.hostid = ' + str(self.host_id),
                                        'd_hostDirItemType.d_dirid = ' + str(self.d_dir_id),
                                        'd_hostDirItemType.d_dirItemTypeid = ' + str(file_type_id) ] ),
                         'order by name asc limit 1'
                         ] )
        xs = pgsqlutil.fetch_all( dbcur, sql )
        dbcur.close()
        return xs

    def get_files4template( self, filenames, cnames ):
        assert len(filenames) == len(cnames)
        # todo: handle Nones here below?
        aka_urls = self.get_aka_url_map( cnames ).values()
        assert len(filenames) == len(aka_urls)
        files = []
        for i in range( 0, len(filenames) ):
            files.append( {'item_name':filenames[i], 'aka_url':aka_urls[i]} )
        return files

    def get_thumbs( self, data ):
        return self.get_thumbs4template( data.cname_id2name )

    def get_thumbs4template( self, cname_id2name ):
        # todo: handle Nones here below?
        cnameids = cname_id2name.keys()
        cnames = cname_id2name.values()
        src_url_map = self.get_thumb_src_url_map( cnameids )
        aka_url_map = self.get_aka_url_map( cnames )
        assert len(cnameids) >= len(src_url_map)
        assert len(cnames) == len(aka_url_map)
        thumbs = []
        for k in src_url_map.keys():
            thumbs.append( {'thumb_src':src_url_map[k], 'aka_url':aka_url_map[k]} )
        return thumbs

    def fileid_to_cnameid( self, file_id ):
        sql = ' '.join( ["select cname.id from cname, cnameid_x_d_hostDirItemTypeid",
                         "where cnameid_x_d_hostDirItemTypeid.cnameid = cname.id",
                           "and cnameid_x_d_hostDirItemTypeid.d_hostDirItemTypeid = " + str(file_id) ]);
        dbcur = self.dbconn.cursor()
        rows = map( lambda e:e['id'], pgsqlutil.fetch_all( dbcur, sql ) )
        dbcur.close();
        assert len(rows) == 1, rows
        return rows[0];

    def cnameid_to_cname( self, id ):
        sql = ' '.join( ['select cname.sum, cname.len from cname where cname.id = ' + str(id)] )
        dbcur = self.dbconn.cursor()
        rows = pgsqlutil.fetch_all( dbcur, sql )
        dbcur.close()
        assert len(rows) == 1, "%s %s" % (str(id), str(rows))
        cname = str(rows[0]['sum'])+"_"+str(rows[0]['len'])        
        return cname

    def get_aka_url( self, base_url, cname ):
        return urlparse.urljoin( base_url, 'aka/' + cname )

    def get_thumb_url( self, base_url, cname_id ):
        # get bytes from database!?
        sql = "with tmp as ( select jpeg from thumbnail where cnameid = " + str(cname_id) + " ) select encode(jpeg, 'base64') from tmp"
        dbcur = self.dbconn.cursor()
        row = pgsqlutil.fetch_one( dbcur, sql )
        dbcur.close()
        if row and len(row) > 0 and row[0]:
            return str("data:image/jpg;base64," + str(row[0]))
        else:
            return None

    def get_aka_url_map( self, cnames ):
        # there's really had better be 1 aka url for each and every one!
        url_map = {}
        if cnames:
            for e in cnames:
                url_map[e] = self.get_aka_url(self.base_url, e)
            assert len(cnames) == len(url_map)
        return url_map

    def get_thumb_src_url_map( self, cname_ids ):
        url_map = {}
        if cname_ids:
            for e in cname_ids:
                url = self.get_thumb_url(self.base_url, e)
                if url:
                    url_map[e] = url
            assert len(cname_ids) >= len(url_map)
        return url_map

    def get_files( self, data ):
        return self.get_files4template( data.filenames, data.cnames )

    def fetch_data( self ):
        file_idXname = self.get_file_idXnames()
        file_ids = []
        filenames = []
        cname_ids = []
        cnames = []
        cname_id2name = {}
        for idXname in file_idXname:
            file_ids.append( idXname['id'] )
            filenames.append( idXname['name'] )
            cname_ids.append( self.fileid_to_cnameid( idXname['id'] ) )
            cnames.append( self.cnameid_to_cname( cname_ids[-1] ) )
            cname_id2name[cname_ids[-1]] = cnames[-1]
        assert_lens( file_idXname, file_ids )
        assert_lens( file_idXname, filenames )
        assert_lens( file_idXname, cname_ids )
        assert_lens( file_idXname, cnames )
        assert_lens( file_idXname, cname_id2name )
        return Data( file_idXname, file_ids, filenames, cname_ids, cnames, cname_id2name )

    def render( self ):
        data = self.fetch_data()
        dirs = self.get_dirs( data )
        files = self.get_files( data )
        thumbs = self.get_thumbs( data )
        t = Template( filename='dir-web.mt' )
        return t.render( dirs=dirs, files=files, thumbs=thumbs )

def application( env, response ):
    response( '200 OK', [('Content-Type', 'text/html; charset=utf-8')] )
    dbconn = db.connect( host="localhost", user="pybak", password="kabyp", database="pybakdb" )
    d = DirWeb( 'http://www.psync-o-pathics.com', 'www.monad.com', '/', dbconn )
    html = d.render()
    dbconn.close()
    return str(html) # god i HATE python.

if __name__ == '__main__':
    dbconn = db.connect( host="localhost", user="pybak", password="kabyp", database="pybakdb" )
    d = DirWeb( 'http://www.psync-o-pathics.com', 'superman-laptop', '/media/Windows/Jon/Application_Data/Flickr/Temp', dbconn )
    print d.render()
    dbconn.close()
