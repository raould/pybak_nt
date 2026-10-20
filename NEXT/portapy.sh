#!/usr/bin/env bash
set -x
python3 "$PORTAPY/scripts/run_docker.py" \
    --all \
    --project /home/superman/Dev/pybak_nt/NEXT \
    --read-only \
    --network-none \
    -- python client.py
set +x
