#!/usr/bin/env bash

docker run \
       -d \
       -v /home/pybak/canonical:/home/pybak/canonical \
       -v /home/pybak/browse:/home/pybak/browse \
       -p 6969:6969 \
       pybakd
