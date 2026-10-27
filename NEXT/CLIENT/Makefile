PYTHONPATH = "/home/superman/Dev/portapy/src:../SHARED"
PORTAPY = "/home/superman/Dev/portapy"

all: check types run3

run3:
	mkdir -p /tmp/test
	cp -r . /tmp/test
	echo "psync-o-pathics.com/browse" > /tmp/test/abrowse.txt
	PYTHONPATH=$(PYTHONPATH) python3 client.py /tmp/test

check:
	export PORTAPY=$(PORTAPY) && \
	python3 $${PORTAPY}/scripts/checkall.py *.py ../SHARED/*.py

docker:
	export PORTAPY=$(PORTAPY) && \
	python3 $(PORTAPY)/scripts/run_docker.py \
		--all \
		--project .. \
		--read-only \
		--network-none \
		-- sh -c 'CRAWL_DIR="/tmp"; PYTHONPATH="$$PYTHONPATH:/workspace/SHARED" exec python CLIENT/client.py $${CRAWL_DIR}'

# mypy --strict over the modules listed in mypy.ini (no stub files to keep in step).
types:
	MYPYPATH=/home/superman/Dev/portapy/src mypy
