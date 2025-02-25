#!/bin/bash

SRCDIR=$1
DSTDIR=$2
if [ -z "${SRCDIR}" ]; then
    echo "require src_dir argument"
    exit 1
fi
if [ -z "${DSTDIR}" ]; then
    echo "require dst_dir argument"
    exit 1
fi

for me in `\ls -1 "$SRCDIR"`; do
    srcfile=`basename ${me}`
    prextn=`echo ${me} | sed 's/....$//'`
    extn=`echo ${me} | sed 's/.*\.//'`
    dstfile=`sum "${SRCDIR}/${me}" | awk -v f=${prextn} -v e=${extn} '{ print f "_" $1 $2 "." e }'`
    echo ${SRCDIR}/${me} ${DSTDIR}/${dstfile}
    ln -s "${SRCDIR}/${me}" "${DSTDIR}/${dstfile}"
done
