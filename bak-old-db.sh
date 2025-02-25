#!/bin/bash
for me in `find . -mindepth 1 -maxdepth 1 -type d | sort -n | tac`; do
	~/Bin/Pybak/client.py ${me} nas;
done
