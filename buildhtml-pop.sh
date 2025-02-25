#!/bin/bash
if [ $# == 0 ]; then
    echo "args: --images-only/--not-images {--test}"
    exit 1
fi
if [ "$1" != "--images-only" -a "$1" != "--not-images" ]; then
    echo "args: --images-only/--not-images {--test}"
    exit 1
fi
if [ "$2" == "--test" ]; then
	sudo ./buildhtml.py $1 --overwrite /tmp/pybak/home/pybak https://www.psync-o-pathics.com canonical browse	
else
	sudo ./buildhtml.py $1 --overwrite /home/pybak https://www.psync-o-pathics.com canonical browse
fi
