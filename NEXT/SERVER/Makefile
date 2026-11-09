# Variables
VENV = venv
FASTAPI = $(VENV)/bin/fastapi
PORTAPY = /home/superman/Dev/portapy
PYTHONPATH = "$(PORTAPY)/src:../SHARED"

.PHONY: run3
run3:
	PYTHONPATH=$(PYTHONPATH) python3 main.py

.PHONY: run-dev
run-dev:
	PYTHONPATH=$(PYTHONPATH) $(FASTAPI) dev main.py

# mypy --strict over main.py and the shared modules (see mypy.ini).
.PHONY: types
types:
	MYPYPATH=$(PORTAPY)/src $(VENV)/bin/mypy
