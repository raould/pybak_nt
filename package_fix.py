#!/usr/bin/env python

import sys
import os
import os.path
import re

def figure_package( root, cwd ):
    head = os.path.split( root )[-1]
    tail = cwd.replace( root, "" ).replace( os.sep, "." )
    package = head + tail
    return package

def fix( cwd, f, package ):
    conent = None
    with open( os.path.join( cwd, f ) ) as rh:
        content = "".join( rh.readlines() )
    if content:
        fixed_content = re.sub( r"""^package.*""", "package " + package, content, 1 )
        with open( os.path.join( cwd, f ), "w" ) as wh:
            wh.write( fixed_content )

root = os.path.abspath( sys.argv[1] )
ok_tails = ["/com","/org","/net"]
ok = reduce( lambda a,b: a or (root.endswith(b)), ok_tails, False )
if not ok:
    sys.stderr.write( "directory doesn't look like a package root, must end with %s: was %s\n" % ( reduce(lambda a,b: a+" or "+b, ok_tails), root ) )
    sys.exit(1)

for cwd, dirs, files in os.walk( root ):
    for f in files:
        if f.endswith( ".scala" ):
            package = figure_package( root, cwd )
            fix( cwd, f, package )
