#!/usr/bin/env bash

# usage:
# (from the pybak git root directory)
# Docker/docker-run-pybakd.sh (if not already running)
# Docker/docker-run-client.sh dir1 dir2 ... dirN pybak

echo "pruning..."
IMAGE_NAME=pybak-client
docker ps --filter "ancestor=${IMAGE_NAME}" --format "{{.Names}}" | xargs -I X docker container stop "X"
docker container prune -f
echo "...done pruning"

NETWORK=pybak-network
docker run \
       --network ${NETWORK} \
       -t \
       pybak-client "$@"

