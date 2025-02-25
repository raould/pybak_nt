#!/usr/bin/env/python

import util
import sys
import time

class TimeIt:

    def __init__( self ):
        self.stack = []
        self.avgPairs = {}
        self.maxs = {}
        self.mins = {}

    def push( self, msg ):
        now = time.time()
        self.stack.append( (msg, now) )

    def pop( self ):
        startTuple = self.stack.pop()
        msg = startTuple[0]

        start = startTuple[1]
        end = time.time()
        diff = int( (end-start) * 1000 )
        
        if not (msg in self.avgPairs):
            self.avgPairs[ msg ] = (diff,1)
        else:
            (od,oc) = self.avgPairs[ msg ]
            self.avgPairs[ msg ] = (od+diff,oc+1)
        (at,ac) = self.avgPairs[ msg ]
        avgD = at/ac

        if not (msg in self.mins):
            self.mins[msg] = diff
        else:
            self.mins[msg] = min( self.mins[msg], diff )
        if not (msg in self.maxs):
            self.maxs[msg] = diff
        else:
            self.maxs[msg] = max( self.maxs[msg], diff )

        minD = self.mins[msg]
        maxD = self.maxs[msg]

        return "%s: %s msec (%s/%s) (%s avg)\n" % ( msg, diff, minD, maxD, avgD )

def test():
    ti = TimeIt()
    for i in range(1,10):
        ti.push( "testing" )
        time.sleep( 0.25 )
        print ti.pop()

if __name__ == '__main__':
    import sys
    if util.eat_arg( sys.argv, "test" ):
	test()
    else:
        sys.stdout.write( "ERROR:\n usage: %s --test\n" % sys.argv[0] )

