#!/usr/bin/env python

import traceback
import timeit
import sys
import re
import platform
import os
import os.path
import util
import metadata
import filespec
import hexlpathutil
import visit_core
import filetypes
import requests
import json
import binascii

MAX_CHUNK_BYTES = 1024 * 1024 * 10
gDryRunFull = "dryrunfull"
gDryRunMissing = "dryrunmissing"
gChecksumCache = {}

class Client:

    def __init__( self, hostname ):
        self.hostname = hostname
        self.timeit = timeit.TimeIt()

    # ----------------------------------------

    def log( self, msg=None, caller=None ):
        visit_core.log( msg, caller )

    # ----------------------------------------

    def get_system_headers( self ):
        return { 'x-hostname' : self.hostname,
                 'x-py-platform-system' : platform.system(),
                 'x-py-platform-uname' : " ".join(platform.uname()),
                 # todo: this is not reliable
                 # since (1) on linux it should really always
                 # just say 'raw bytes', and (2) i do not believe
                 # this looks at the underlying fs e.g.
                 # if you have user-space mounted some fs with
                 # different encodings than 'normal' for that os.
                 'x-py-sys-filesystemencoding' : sys.getfilesystemencoding(),
                 'x-py-sys-byteorder' : sys.byteorder,
                 'x-py-os-path-sep' : os.path.sep }

    # ----------------------------------------

    def match_dir( self, ip, port, dirpath, dry_run, max_depth, cur_depth, max_bytes ):
        url = "http://%s:%s/%s" % (ip, port, "match-list")
        headers = self.get_system_headers()
        gChecksumCache = {}
        dir_entries = self.get_dir_entries( dirpath, max_bytes )
        dir_json = self.dir_entries_to_json( dir_entries )
        if dir_json is not None:
            self.log( "[client->]\theaders = %s\njson = %s\n" % (headers, dir_json) )
            r = requests.post( url, data=dir_json, headers={'x-headers':json.dumps(headers)} )
            self.log( "[client<-]\ttext = %s\n" % r.text )
            remote_wanted = json.loads( r.text )
            self.log( "[client<-]\tremote_wanted = %s\n" % remote_wanted )
            self.log( "[client<->]\t#->%s, #<-%s\n" % (str(len(dir_entries)), str(len(remote_wanted))) )
            self.send_dir_updates( remote_wanted, ip, port, dry_run, max_depth, cur_depth )

    def send_dir_updates( self, remote_wanted, ip, port, dry_run, max_depth, cur_depth ):
        filepaths_to_update = map( lambda e: binascii.unhexlify(e["hexl-filepath"]), remote_wanted )
        self.log( "[client<-]\tquery = %s\n" % filepaths_to_update )
        return self.save_direntries_throws( ip, port, filepaths_to_update, dry_run, max_depth, cur_depth )

    def dir_entries_to_json( self, data ):
        if len(data) == 0:
            return None
        else:
            return json.dumps(data)

    def get_dir_entries( self, dirpath, max_bytes ):
        self.log( "get_dir_entries: %s\n" % dirpath )
        data = []
        try:
            files = os.listdir( dirpath )
        except:
            self.log( "[client]\tERROR\t%s" % sys.exc_info()[0] )
            return data
        self.log( "[client]\t#%s\n" % len(files) )
        for i in range(len(files)):
            f = files[i]
            filepath = os.path.abspath( os.path.join( dirpath, f ) )
            isfile = os.path.isfile( filepath )
            if isfile:
                size = util.get_file_length( filepath )
                self.log( "[client]\t%s/%s %s (file)\n" % (i+1, len(files), size) )
                if visit_core.is_cache_path( filepath ):
                    continue
                if max_bytes is None or size <= max_bytes:
                    data.append( self.get_fileheaders( filepath ) )
                else:
                    self.log( "[client] file too big, skipping!\n" )
            else:
                self.log( "[client]\t%s/%s (dir)\n" % (i+1, len(files)) )
        return data

    def get_fileheaders( self, filepath ):
        csum = util.calculate_checksum( filepath )
        length = util.get_file_length( filepath )
        assert csum is not None, filepath
        assert length is not None, filepath
        is_c = util.smells_like_canonical( filepath )
        is_md = util.smells_like_any_metadata( filepath )
        f2c = util.get_checksum_from_path( filepath )
        f2l = util.get_length_from_path( filepath )
        gChecksumCache[filepath] = csum
        assert gChecksumCache[filepath] == csum, filepath
        data = self.get_file_headers(
            filepath,
            csum,
            length,
            is_c,
            is_md,
            f2c,
            f2l
        )
        return data

    # ----------------------------------------

    def get_file_headers( self, filepath, checksum, length, is_c, is_md, f2c, f2l, offset=0 ):
        assert filepath
        assert checksum
        assert length is not None
        file_headers = { 'x-hexl-filepath' : binascii.hexlify(filepath),
                         'x-hexl-filepath-parts' : hexlpathutil.path_to_hexl_list(filepath),
                         'x-checksum' : checksum,
                         'x-length' : length,
                         'x-is-canonical' : is_c,
                         'x-is-metadata' : is_md,
                         'x-f2c' : f2c,
                         'x-f2l' : f2l,
                         'x-offset' : offset,
                         'x-isexe' : util.is_executable(filepath),
                         'x-oldest' : util.get_file_oldest_seconds(filepath) }
        return file_headers

    # ----------------------------------------

    def setup_file_request( self, ip, port, action, filepath, checksum, length, offset ):
        url = "http://%s:%s/%s" % (ip, port, action)
        is_c = util.smells_like_canonical( filepath )
        is_md = util.smells_like_any_metadata( filepath )
        f2c = util.get_checksum_from_path( filepath )
        f2l = util.get_length_from_path( filepath )
        fi = self.get_file_headers( filepath, checksum, length, is_c, is_md, f2c, f2l, offset )
        si = self.get_system_headers()
        headers = dict( fi.items() + si.items() )
        # assert early on client side by converting once to filespec vs. too much later on server side.
        try:
            spec = filespec.FileSpec.from_headers( headers )
            self.log( str(spec) )
        except AssertionError:
            visit_core.log_error( str([filepath, checksum, length, offset]) )
        return (url, headers)

    def get_remote_length( self, ip, port, filepath, checksum, length ):
        def inner( self, ip, port, filepath, checksum, length ):
            (url, headers) = self.setup_file_request( ip, port, "get-length", filepath, checksum, length, 0 )
            self.log( "[client->]\tget-length:\nheaders=%s\turl=%s\n" % (headers, url) )
            r = requests.post( url, headers={'x-headers':json.dumps(headers)} )
            if r.status_code == 200:
                remote_length_code = r.headers.get( 'x-length' )
                self.log( "[client<-]\tremote length code = %s\n" % remote_length_code )
                if remote_length_code is not None:
                    remote_length = int( remote_length_code )
                    return remote_length
            elif r.status_code > 400:
                return length # force not sending.
            else:
                self.log( "[client<-]\tassuming length = 0 (status %s)\n" % r.status_code )
                return 0
        #self.timeit.push( "get_remote_length" )
        result = inner( self, ip, port, filepath, checksum, length )
        #self.log( "get_remote_length: done %s -> %s\n" % ( self.timeit.pop(), result ) )
        return result

    def save_dir( self, ip, port, dirpath, dry_run, max_depth, cur_depth ):
        def inner( self, ip, port, dirpath, dry_run, max_depth, cur_depth ):
            try:
                return self.save_dir_throws( ip, port, dirpath, dry_run, max_depth, cur_depth )
            except Exception:
                visit_core.log_error( "ERROR %s\n" % dirpath )
                raise
        if visit_core.is_too_deep( max_depth, cur_depth ):
            return False
        else:
            #self.timeit.push( "save_dir" )
            result = inner( self, ip, port, dirpath, dry_run, max_depth, cur_depth )
            # self.log( self.timeit.pop() )
            return result

    def save_dir_throws( self, ip, port, dirpath, dry_run, max_depth, cur_depth ):
        entries = [os.path.join( dirpath, f ) for f in os.listdir(dirpath)]
        return self.save_direntries_throws( ip, port, entries, dry_run, max_depth, cur_depth )

    def save_direntries_throws( self, ip, port, entries, dry_run, max_depth, cur_depth ):
        def inner( self, ip, port, entries, dry_run, max_depth, cur_depth ):
            if visit_core.is_too_deep( max_depth, cur_depth ):
                return False
            dirs = []
            failed = []
            for e in entries:
                self.log( "[client->]\tchecking %s\n" % e )
                assert os.path.exists( e )
                if os.path.isfile( e ):
                    self.log( "[client->]\tis file\n" )
                    success = self.save_file( ip, port, e, dry_run )
                    if not success:
                        failed.append( e )
                elif os.path.isdir( e ):
                    dirs.append( e )
                else:
                    self.log( "[client->]\twtf? %s\n" % e )
            for d in dirs:
                self.save_dir( ip, port, d, dry_run, max_depth, cur_depth+1 ) # yes, ignoring result.
            if failed:
                visit_core.log_error( "FAILED: %s files failed.\n" % len(failed) )
            return True
        #self.timeit.push( "save_dir_throws" )
        result = inner( self, ip, port, entries, dry_run, max_depth, cur_depth )
        # self.log( self.timeit.pop() )
        return result

    def save_file( self, ip, port, filepath, dry_run=None ):
        def inner( self, ip, port, filepath, dry_run=None ):
            try:
                filepath = os.path.abspath( filepath )
                success = self.save_file_throws(ip, port, filepath, dry_run)
                if not success:
                    visit_core.log_error( "FAILED: %s\n" % filepath )
                return success
            except Exception:
                visit_core.log_error( "ERROR %s\n" % filepath )
                raise
        #self.timeit.push( "save_file" )
        result = inner( self, ip, port, filepath, dry_run=None )
        # self.log( self.timeit.pop() )
        return result

    def save_file_throws( self, ip, port, filepath, dry_run ):
        def inner( self, ip, port, filepath, dry_run ):
            length = util.get_file_length( filepath )
            if filepath in gChecksumCache:
                checksum = gChecksumCache[filepath]
            else:
                self.log( "[client]\tmissing checksum in cache!" )
                checksum = util.calculate_checksum( filepath )
            assert checksum, [filepath, gChecksumCache]
            self.log( "[client]\t%s length = %s, sum = %s\n" % (filepath, length, checksum) )
            if length > 0:
                if dry_run == gDryRunFull:
                    self.log( "save_file_throws(): dry run %s\n" % filepath )
                    return True

                part_length = self.get_remote_length( ip, port, filepath, checksum, length )
                self.log( "[client<-]\t%s remote length = %s; local length = %s\n" % (filepath, part_length, length) )

                if part_length is not None and int(length) == int(part_length):
                    self.log( "[client<-]\tsame length case\n" )
                    if dry_run != gDryRunMissing:
                        self.log( "[client<-]\talready done = %s\n" % filepath )
                else:
                    self.log( "[client<-]\tmissing (%s) = %s -> %s\n" % ( part_length/length, filepath, util.get_data_path('server', checksum, length) ) )
                    if dry_run:
                        return True
                    offset = (part_length, 0)[part_length is None]
                    success = self.save_file_offset( ip, port, filepath, checksum, length, offset )
                    if not success:
                        return False
            else:
                self.log( "[client->]\tskipping zero length file %s\n" % filepath )
            return True
        #self.timeit.push( "save_file_throws" )
        result = inner( self, ip, port, filepath, dry_run )
        # self.log( self.timeit.pop() )
        return result
    
    def save_file_offset( self, ip, port, filepath, checksum, length, offset ):
        def inner( self, ip, port, filepath, checksum, length, offset ):
            self.log( "[client->]\tsave_file_offset( %s, %s, %s, %s, %s, %s )\n" % ( ip, port, filepath, checksum, length, offset ) )
            is_md = util.smells_like_any_metadata( filepath )
            success = True
            if is_md:
                # writing the whole/remaining thing in one go.
                chunk_size = length
                success = self.save_md( ip, port, filepath )
            else:
                cursor = offset
                while cursor < length and success:
                    chunk_size = min(length - cursor, MAX_CHUNK_BYTES)
                    success = self.save_chunk( ip, port, filepath, checksum, length, cursor, chunk_size )
                    cursor += chunk_size
            return success
        #self.timeit.push( "save_file_offset" )
        result = inner( self, ip, port, filepath, checksum, length, offset )
        # self.log( self.timeit.pop() )
        return result

    def save_md( self, ip, port, filepath ):
        self.log( "[client->]\tsave_md( %s )\n" % filepath )
        assert util.smells_like_any_metadata( filepath ), "expected metadata"
        md = metadata.read_both_in_path( filepath )
        if md is not None:
            md_json = metadata.to_json( md )
            jfp = re.sub( metadata.PICKLE_DOTEXT, metadata.JSON_DOTEXT, filepath )
            checksum = util.get_checksum_from_path( filepath )
            length = util.get_length_from_path( filepath )
            (url, headers) = self.setup_file_request( ip, port, "save-md", jfp, checksum, length, 0 )
            r = requests.post( url, data=md_json, headers={'x-headers':json.dumps(headers)} )
            return r.status_code == 200
        return False

    def save_chunk( self, ip, port, filepath, checksum, length, offset, chunk_size ):
        def inner( self, ip, port, filepath, checksum, length, offset, chunk_size ):
            self.log( "[client->]\tsave_chunk(): l=%s o=%s c=%s\n" % ( length, offset, chunk_size ) )
            (url, headers) = self.setup_file_request( ip, port, "save-chunk", filepath, checksum, length, offset )
            fileh = open( filepath, "rb" )
            fileh.seek( offset )
            chunk = fileh.read( chunk_size )
            try:
                r = requests.post( url, data=chunk, headers={'x-headers':json.dumps(headers)} )
                return r.status_code == 200
            finally:
                fileh.close()
        #self.timeit.push( "save_chunk" )
        result = inner( self, ip, port, filepath, checksum, length, offset, chunk_size )
        # self.log( self.timeit.pop() )
        return result

def usage(msg=None):
    if msg:
        visit_core.log_error("[%s]\n" % msg)
    visit_core.log_error( "ERROR:\n" )
    visit_core.log_error( " usage: %s {--dryrun,--missing} {--maxdepth N} {--maxbytes B} {--images} <root of tree to send> <dst ip/host name>\n" % sys.argv[0] )
    visit_core.log_error( " was: %s\n" % " ".join( sys.argv ) )
    sys.exit()

def visit_file( file_count, full_path, data ):
    # TODO: now we're just doing it by directories via visit_pre_dir.
    # clean all this sh*t up. and support images-only in visit_pre_dir etc.
    # (and rewrite all this, in some other language too, oy veh.)
    return

def visit_pre_dir_with_client( dirpath, max_depth, cur_depth, opts, ip, port, dry_run, client ):
    if not visit_core.is_too_deep( max_depth, cur_depth ) and not visit_core.is_cache_path( dirpath ):
        assert os.path.isdir( dirpath ), dirpath
        visit_core.log( "visit_pre_dir_with_client: %s\n" % dirpath )
        client.match_dir( ip, port, dirpath, dry_run, max_depth, cur_depth, opts['max_bytes'] )

if __name__ == '__main__':
    from socket import gethostname

    dry_run = None
    images = None

    # have i mentioned recently what a ton of shit my old arg related code is here?

    found_args = visit_core.main_helper( usage )
    if found_args['max_depth'] and found_args['max_depth'] <= 0:
        found_args['dry_run'] = True
    # be slightly less unlike 'find'.
    if found_args['max_depth']:
        found_args['max_depth'] = found_args['max_depth'] - 1

    if found_args['dry_run']:
        dry_run = gDryRunFull

    if util.eat_arg(sys.argv, "missing", remove=True):
        if found_args['dry_run']:
            usage( "--dryrun and --missing are mutually exclusive." )
        dry_run = gDryRunMissing

    if util.eat_arg(sys.argv, "images", remove=True):
        images = True;

    try:
        # e.g. client.py dir1 dir2 dir3 192.168.123.211
        all_dirs = sys.argv[1:-1]
        ip = sys.argv[-1]
        # todo: support overriding the port, parse "ip:port".
        port = "6969"
        print("PARAMETERS=", all_dirs, ip, port)
        client = Client( gethostname() )
    except:
        sys.stderr.write( "usage exception: %s\n" % traceback.format_exception( *sys.exc_info() ) )
        usage(msg=(sys.exc_info()[0]))
    for a in sys.argv:
        if a[0] == "-" or a[0] == "--":
            usage( "unknown flag: %s" % a )
    try:
        def visit_pre_dir( dirpath, max_depth, cur_depth, opts ):
            return visit_pre_dir_with_client( dirpath, max_depth, cur_depth, opts, ip, port, dry_run, client )
        for root in all_dirs:
            visit_core.log( "[client] root=%s ip=%s port=%s\n" % (root, ip, port) )
            f = visit_core.visit( root, found_args['max_depth'], visit_file, visit_pre_dir, {'max_bytes':found_args['max_bytes']} )
            print "visited %s file(s)" % f
    except:
        sys.stderr.write( "client hit exception: %s\n" % traceback.format_exception( *sys.exc_info() ) )
