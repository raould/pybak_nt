# Variables
VENV = venv
PORTAPY = /home/superman/Dev/portapy
PYTHONPATH = "$(PORTAPY)/src:../SHARED"

.PHONY: run3
run3:
	. $(VENV)/bin/activate; PYTHONPATH=$(PYTHONPATH) python3 main.py

# mypy --strict over main.py and the shared modules (see mypy.ini).
.PHONY: types
types:
	MYPYPATH=$(PORTAPY)/src $(VENV)/bin/mypy
