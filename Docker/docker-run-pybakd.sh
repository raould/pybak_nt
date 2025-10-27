#!/usr/bin/env bash

IMAGE_NAME=pybakd
docker ps --filter "ancestor=${IMAGE_NAME}" --format "{{.Names}}" | xargs -I X docker container stop "X"
docker container prune

NETWORK=pybak-network
docker network create ${NETWORK}
docker run \
       --name pybakd1 \
       --network ${NETWORK}
       -d \
       -v /home/pybak/canonical:/home/pybak/canonical \
       -v /home/pybak/browse:/home/pybak/browse \
       -p 6969:6969 \
       pybakd
