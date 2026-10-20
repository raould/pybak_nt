all: check run

run3:
	PYTHONPATH="/home/superman/Dev/portapy/src" python3 /home/superman/Dev/pybak_nt/NEXT/client.py /tmp/test

check:
	export PORTAPY="/home/superman/Dev/portapy" && python3 $${PORTAPY}/scripts/checkall.py client.py

docker:
	export PORTAPY="/home/superman/Dev/portapy" && \
	python3 $${PORTAPY}/scripts/run_docker.py \
		--all \
		--project /home/superman/Dev/pybak_nt/NEXT \
		--read-only \
		--network-none \
		-- python client.py /workspace
