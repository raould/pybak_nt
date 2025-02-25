import pwd
import sys
import util
import metadata
import timeit
import os
import os.path
import json
import filespec
import binascii
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

gReadChunkLen = 1024*512

# server:
#
# (0) check json directory of files.
#
# (A external api) given (hostname, path, checksum, length)
#  (1) if data:(checksum, length) [B]
#   (1.1) does exist, update metadata:(hostname, path), return 200. [D]
#   (1.2) doesn't exist, return 404.
#
# (B) given data:(checksum, length)
#  (1) return does exist: $STORAGE_BASE/checksum[0:gChecksumSplitLength]/checksum_length
#
# (C external api) given (hostname, path, checksum, length, data/stream)
#  (1) write the stream to $STORAGE_BASE/checksum[0:gChecksumSplitLength]/checksum_length
#  (2) and merge {hostname:[path]} into $STORAGE_BASE/checksum[0:gChecksumSplitLength]/checksum_length.metadata [D]
#
# (D) given (hostname, path, checksum, length)
#  (1) merge {hostname:[path]} into $STORAGE_BASE/checksum[0:gChecksumSplitLength]/checksum_length.metadata

class Server:

    def log_error( self, msg ):
        sys.stderr.write( msg )
        
    def log( self, msg ):
        sys.stdout.write( msg )

    def __init__( self, base_dir, bak_subdir ):
        self.base_dir = os.path.abspath( base_dir )
        self.bak_root = os.path.abspath( os.path.join( base_dir, bak_subdir ) )
        self.chunk_size = gReadChunkLen
        self.timeit = timeit.TimeIt()
        print self.__dict__

    def get_data_path( self, checksum, length ):
        return util.get_data_path( self.bak_root, checksum, length )

    def get_metadata_path( self, checksum, length ):
        return util.get_json_metadata_path( self.bak_root, checksum, length )
    
    # ------------------------------

    def match_list( self, params, stream, length ):
        self.log( "[->server] match_list: %s, %s\n" % (params, length) )
        response_lines = []
        dicts_json = stream.read( length )
        self.log( "[->server] match_list: dicts_json = %s\n" % dicts_json )
        dicts = json.loads( dicts_json )
        self.log( "[->server] match_list: dicts = %s\n" % dicts )
        for i in range( 0, len(dicts) ):
            d = dict( dicts[i].items() + params.items() )
            self.log( "[->server] match_list: match_file %s\n" % d )
            match_code = self.match_file( d )
            wanted = isinstance(match_code, filespec.FileSpec)
            if wanted:
                response_lines.append( match_code.toJson() )
                self.log("[->server] want %s\n" % match_code.clear_filepath)
            self.log( "[->server] %s\t/ %s\t-> wanted? %s\n" % (i+1, len(dicts), wanted) )
        response_json = "[%s]" % ",\n".join( response_lines )
        self.log( "[<-server] match_list: returning response_json\n" )
        return response_json
    
    def match_file( self, params ):
        self.log( "[server] match_file: %s\n" % params )
        spec = filespec.FileSpec.from_headers( params )
        data_path = self.get_data_path( spec.checksum, spec.length )
        self.log( "[server] match_file: data_path = %s\n" % data_path )
        local_length = util.get_file_length( data_path )
        completed = local_length == spec.length
        self.log( "[->server] completed? %s\n" % completed )
        if self.smells_like_pybak_to_ignore( spec.clear_filepath ):
            self.log( "[->server] ignore self\n" )
            return -403
        if spec.is_metadata:
            self.log( "[->server] resend md\n" )
            return spec
        if spec.is_canonical and spec.f2c and spec.f2l:
            sane = spec.f2c == spec.checksum
            if not sane:
                self.log( "[->server] ignore not sane canonical\n" )
                return -403
            elif os.path.exists( data_path ) and completed:
                self.log( "[->server] ignore completed canonical\n" )
                return -200
            else:
                self.log( "[->server] resend canonical\n" )
                return spec
        else:
            self.update_metadata_from_spec( spec )
            if os.path.exists( data_path ) and completed:
                return -200
        return spec

    def get_length( self, params ):
        spec = filespec.FileSpec.from_headers( params )
        if spec.is_metadata:
            return 0 # force getting full md for merging.
        else:
            data_path = self.get_data_path( spec.checksum, spec.length )
            local_length = util.get_file_length( data_path )
            return local_length

    def smells_like_pybak_to_ignore( self, path ):
        # don't recrawl our own self, but if we are
        # crawling other/older pybak storage, we do want to merge it.
        b = util.has_base( self.bak_root, path )
        return b

    # ------------------------------

    def save_md( self, params, stream, length ):
        spec = filespec.FileSpec.from_headers( params )
        j = stream.read( length )
        md = json.loads( j )
        metadata.update_from_md( self.bak_root, spec, md )
        return True

    # ------------------------------

    def save_chunk( self, data, stream ):
        def inner( self, data, stream ):
            (offset, span) = (data['x-offset'], data['x-chunk-length'])
            (checksum, length) = (data['x-checksum'], data['x-length'])
            p = self.get_data_path( checksum, length)
            self.log( "[->server] save_chunk( %s, %s, @%s, +%s )\n" % (checksum, length, offset, span) )
            # write_stream can raise AlreadyCompleted.
            self.write_stream( checksum, length, offset, stream, span )
            if util.get_file_length( p ) >= length:
                # other routes only do length checks, so we have to remove the bad files here.
                valid = util.validate_checksum_length( self.bak_root, checksum, length )
                if not valid:
                    self.log_error( "[->server] final validation failed, removing %s\n" % p )
                    util.remove( p )
                    util.remove( self.get_metadata_path( checksum, length ) )
                return valid
            else:
                return True
        #self.timeit.push( "save_chunk" )
        result = inner( self, data, stream )
        #self.log( self.timeit.pop() )
        return result

    def update_metadata_from_spec( self, spec ):
        def inner( self, spec ):
            # don't want to pollute with copies from other pybakd dbs.
            if not spec.is_canonical and not spec.is_metadata:
                metadata.update_from_spec( self.bak_root, spec )
                data_path = self.get_data_path( spec.checksum, spec.length )
                if os.path.exists( data_path ) and util.get_file_length( data_path ) == spec.length:
                    self.chmod( data_path )
                    self.log( "[->server] complete %s %s\n" % (spec.checksum, spec.length) )
        #self.timeit.push( "update_metadata" )
        result = inner( self, spec )
        #self.log( self.timeit.pop() )
        return result

    def chmod( self, data_path ):
        def inner( self, data_path ):
            import stat
            perms = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            perms |= stat.S_IWUSR
            os.chmod( data_path, perms )
            os.chmod( util.data_to_json_metadata_path( data_path ), perms )
        #self.timeit.push( "chmod" )
        result = inner( self, data_path )
        #self.log( self.timeit.pop() )
        return result

    def write_stream( self, checksum, length, offset, stream, stream_length ):
        def inner( self, checksum, length, offset, stream, stream_length ):
            data_path = self.get_data_path( checksum, length )
            self.log( "[->server] _write_stream(): data_path = %s, l = %s\n" % ( data_path, stream_length ) )
            if os.path.exists( data_path ) and util.get_file_length( data_path ) == stream_length and stream_length == length:
                self.log_error( "[<-server] AlreadyCompleted %s %s %s" % (checksum, length, data_path) )
                raise util.AlreadyCompleted( "%s %s %s" % (checksum, length, data_path) )
            else:
                self.write_stream_chunks( data_path, offset, stream, stream_length )
        #self.timeit.push( "write_stream" )
        result = inner( self, checksum, length, offset, stream, stream_length )
        #self.log( self.timeit.pop() )
        return result

    def write_stream_chunks( self, data_path, offset, stream, stream_length ):
        def inner( self, data_path, offset, stream, stream_length ):
            self.log( "[->server] _write_stream_chunks( %s, %s, %s, %s )\n" % ( data_path, offset, stream, stream_length ) )
            util.ensure_parent_path( data_path )
            if os.path.exists( data_path ):
                f = open( data_path, "r+b" )
            else:
                f = open( data_path, "wb" )
            if offset:
                f.seek( offset )

            len_so_far = 0
            chunk = stream.read( self.len_to_read( stream_length, len_so_far ) )

            while chunk and len(chunk)>0 and len_so_far < stream_length:
                len_so_far += len(chunk)
                f.write( chunk )
                if len_so_far < stream_length:
                    chunk = stream.read( self.len_to_read( stream_length, len_so_far ) )

            f.close()
            assert os.path.exists( data_path ), data_path
        #self.timeit.push( "write_stream_chunks" )
        result = inner( self, data_path, offset, stream, stream_length )
        #self.log( self.timeit.pop() )
        return result

    def len_to_read( self, stream_length, len_so_far ):
        def inner( self, stream_length, len_so_far ):
            remaining = stream_length - len_so_far
            return min( remaining, self.chunk_size )
        #self.timeit.push( "len_to_read" ) ### too verbose.
        result = inner( self, stream_length, len_so_far )
        #self.log( self.timeit.pop() )
        return result
