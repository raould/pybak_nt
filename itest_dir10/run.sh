#!/bin/bash

set -x
rm -rf /tmp/pybak
../pybakd.py -test &
sleep 1
PID=`ps auxwwf|grep python | grep pybak | awk '{print $2}'`

../client.py data localhost 1234
MD=`find /tmp/pybak -name *.mdj | head -1`

echo "+++ md before ($MD)"
(pushd ..; python -c "import metadata as md; import sys; m=md.read_json_path(sys.argv[1]); print(md.unhexlify_md(m));" $MD)

../client.py dupe-canonical localhost 1234

echo "+++ md after ($MD)"
(pushd ..; python -c "import metadata as md; import sys; m=md.read_json_path(sys.argv[1]); print(md.unhexlify_md(m));" $MD)

kill $PID
set +x


