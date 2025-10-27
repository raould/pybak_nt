#!/usr/bin/env bash

if [ -f "Dockerfile.pybakd" ] || [ -f "Dockerfile.client" ]; then
    echo "I must be run from the pybak git root directory."
    exit 1
fi

docker rm -f pybakd-docker
docker rm -f pybakd
docker build -t pybakd -f Docker/Dockerfile.pybakd .

docker rm -f pybak-client
docker build -t pybak-client -f Docker/Dockerfile.client .
