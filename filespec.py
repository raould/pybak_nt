#!/usr/bin/env python

import util
import hexlpathutil
import os
import sys
import json
import binascii

class FileSpec:
    def log( self, msg ):
        sys.stdout.write( msg )

    def __init__( self, **kwargs ):

        assert len(kwargs) >= 14, "len=%s kwargs=%s\n" % (len(kwargs), kwargs)
        assert 'hostname' in kwargs, kwargs
        assert 'py_platform_system' in kwargs, kwargs
        assert 'py_platform_uname' in kwargs, kwargs
        assert 'py_byteorder' in kwargs, kwargs
        assert 'py_filepath_encoding' in kwargs, kwargs
        assert 'py_path_sep' in kwargs, kwargs
        assert 'hexl_filepath' in kwargs, kwargs
        assert 'hexl_filepath_parts' in kwargs, kwargs
        assert 'checksum' in kwargs, kwargs
        assert 'length' in kwargs, kwargs
        assert 'is_canonical' in kwargs, kwargs
        assert 'is_metadata' in kwargs, kwargs
        # f2c, fl2 are optional.
        assert 'isexe' in kwargs, kwargs
        assert 'oldest' in kwargs, kwargs

        self.hostname = kwargs.get('hostname')
        self.py_filepath_encoding = kwargs.get('py_filepath_encoding')
        if self.py_filepath_encoding != None:
            self.py_filepath_encoding = self.py_filepath_encoding.lower()
        self.py_platform_system = kwargs.get('py_platform_system')
        self.py_platform_uname = kwargs.get('py_platform_uname')
        self.py_byteorder = kwargs.get('py_byteorder')
        self.py_path_sep = kwargs.get('py_path_sep')

        self.hexl_filepath = kwargs.get('hexl_filepath')
        assert hexlpathutil.to_hexl_path( self.hexl_filepath ) == self.hexl_filepath, kwargs
        self.hexl_filepath_parts = kwargs.get('hexl_filepath_parts')

        self.checksum = kwargs.get('checksum')
        self.length = kwargs.get('length')
        self.is_canonical = kwargs.get('is_canonical')
        self.is_metadata = kwargs.get('is_metadata')
        self.f2c = kwargs.get('f2c')
        self.f2l = kwargs.get('f2l')
        self.isexe = kwargs.get('isexe')
        self.oldest = kwargs.get('oldest')
        self.clear_filepath = hexlpathutil.to_ascii_path(self.hexl_filepath)
        self.clear_filepath_parts = map(lambda e: binascii.unhexlify(e), self.hexl_filepath_parts)

        assert self.hostname, str(self)
        assert self.py_platform_system, str(self)
        assert self.py_platform_uname, str(self)
        assert self.py_byteorder, str(self)
        assert self.py_path_sep, str(self)

        assert self.hexl_filepath, str(self)
        assert self.hexl_filepath_parts != None, str(self)
        # py_filepath_encoding allowed to be None, == raw bytes.
        # self.clear_filepath might have failed.
        assert self.checksum, str(self)
        assert self.length != None, str(self)
        assert self.is_canonical != None, str(self)
        assert self.is_metadata != None, str(self)
        # f2c, f2l are optional.
        assert self.oldest != None, str(self)

    def from_headers( params ):
        # a little paranoid, but sanitize host names.
        return FileSpec( hostname=util.to_ascii_string(params['x-hostname']),
                         py_platform_system=params['x-py-platform-system'],
                         py_platform_uname=params['x-py-platform-uname'],
                         py_filepath_encoding=params['x-py-sys-filesystemencoding'],
                         py_byteorder=params['x-py-sys-byteorder'],
                         py_path_sep=params['x-py-os-path-sep'],
                         hexl_filepath=params['x-hexl-filepath'],
                         hexl_filepath_parts=params['x-hexl-filepath-parts'],
                         checksum=params['x-checksum'],
                         length=params['x-length'],
                         is_canonical=params['x-is-canonical'],
                         is_metadata=params['x-is-metadata'],
                         f2c=params['x-f2c'],
                         f2l=params['x-f2l'],
                         oldest=params['x-oldest'],
                         isexe=params['x-isexe'] )
    from_headers = staticmethod(from_headers)

    def __str__( self ):
        return " ".join(
            map( lambda k:str("(%s:%s)" % (k, getattr(self,k))),
                 [
                     'hostname',
                     'py_platform_system',
                     'py_platform_uname',
                     'py_byteorder',
                     'py_path_sep',
                     'hexl_filepath',
                     'hexl_filepath_parts',
                     'py_filepath_encoding',
                     'checksum',
                     'length',
                     'is_canonical',
                     'is_metadata',
                     'f2c',
                     'f2l',
                     'isexe',
                     'oldest'
                    ]
                 ) )

    def toJson( self ):
        data = {
            "hostname": self.hostname,
            "py-filepath-encoding": self.py_filepath_encoding,
            "py-platform-system" : self.py_platform_system,
            "py-platform-uname" : self.py_platform_uname,
            "py-byteorder" : self.py_byteorder,
            "py-path-sep" : self.py_path_sep,
            "hexl-filepath": self.hexl_filepath,
            "hexl-filepath-parts": self.hexl_filepath_parts,
            "checksum": self.checksum,
            "length": self.length,
            "is-canonical": self.is_canonical,
            "is-metadata": self.is_metadata,
            "f2c": self.f2c,
            "f2l": self.f2l,
            "isexe": self.isexe,
            "oldest": self.oldest
        }
        return json.dumps( data, separators=(',', ':') )

def test():
    files = os.listdir( "./itest_dir4" )
    specs = map( lambda n:
                     FileSpec( hostname='host1',
                               py_filepath_encoding="utf-8",
                               py_platform_system='pps',
                               py_platform_uname='uname',
                               py_byteorder='little',
                               py_path_sep='/',
                               hexl_filepath=binascii.hexlify(n),
                               hexl_filepath_parts=hexlpathutil.path_to_hexl_list(n),
                               checksum='123',
                               length='1',
                               is_canonical=True,
                               is_metadata=False,
                               # f2c, f2l are optional.
                               isexe=False,
                               oldest=1 ),
                 files )
    print "\n".join( map( lambda e: e.toJson(), specs ) )
    print "\n".join( map( lambda e: str(e), specs ) )
    #print "\n".join( map( lambda b: str(b), map( lambda e: isinstance( e, FileSpec ), specs ) ) )
    spec_map = { 0 : specs[0].clear_filepath,
                 1 : specs[1].clear_filepath }
    print spec_map

if __name__ == '__main__':
    if util.eat_arg( sys.argv, "test" ):
	test()
    elif util.eat_arg( sys.argv, "dump" ):
        dump()
    else:
        sys.stdout.write( "usage: %s {--test | --dump <path>}\n" % sys.argv[0] )
