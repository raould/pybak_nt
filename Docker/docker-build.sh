#!/usr/bin/env bash

if [ -f "Dockerfile.pybakd" ] || [ -f "Dockerfile.client" ]; then
    echo "I must be run from the pybak git root directory."
    exit 1
fi

DAEMON=pybakd
docker rm -f pybakd-docker
docker rm -f ${DAEMON}
docker build -t ${DAEMON} -f Docker/Dockerfile.pybakd .

CLIENT=pybak-client
docker rm -f ${CLIENT}
docker build -t ${CLIENT} -f Docker/Dockerfile.client .

docker container prune -f
docker image prune -f
docker image list


