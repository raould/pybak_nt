#!/usr/bin/env bash

docker run \
       -v /home/pybak/canonical:/home/pybak/canonical \
       -v /home/pybak/browse:/home/pybak/browse \
       -p 6969:6969 \
       pybakd-docker
