#!/bin/sh 

for test in save_dir append; do
	echo "---------- STARTING $test";
	python ./itest_full.py $test;
done

for test in save_thrash match save_small; do
	echo "---------- STARTING $test";
    python ./itest_full.py $test;
    python ./itest_full.py $test prewrite;
done





