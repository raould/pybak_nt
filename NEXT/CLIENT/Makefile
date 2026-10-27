all: check types test run3

run3:
	mkdir -p /tmp/test
	cp -r . /tmp/test
	echo "psync-o-pathics.com/browse" > /tmp/test/abrowse.txt
	PYTHONPATH="/home/superman/Dev/portapy/src" python3 /home/superman/Dev/pybak_nt/NEXT/client.py /tmp/test

check:
	export PORTAPY="/home/superman/Dev/portapy" && python3 $${PORTAPY}/scripts/checkall.py *.py

docker:
	export PORTAPY="/home/superman/Dev/portapy" && \
	python3 $${PORTAPY}/scripts/run_docker.py \
		--all \
		--project /home/superman/Dev/pybak_nt/NEXT \
		--read-only \
		--network-none \
		-- python client.py /workspace

# mypy --strict over the modules listed in mypy.ini (no stub files to keep in step).
types:
	MYPYPATH=/home/superman/Dev/portapy/src mypy

test:
	PYTHONPATH="/home/superman/Dev/portapy/src:." python3 test_naming.py
