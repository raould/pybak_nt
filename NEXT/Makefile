all: check run

run:
	PYTHONPATH="/home/superman/Dev/portapy/src" python3 /home/superman/Dev/pybak_nt/NEXT/client.py /tmp

check:
	export PORTAPY="/home/superman/Dev/portapy" && python3 $${PORTAPY}/scripts/checkall.py client.py

docker:
	export PORTAPY="/home/superman/Dev/portapy" && ./portapy.sh
