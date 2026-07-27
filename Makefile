PYTHON ?= python
PIP ?= $(PYTHON) -m pip
SRC := attacks products tests gateway_server.py spec_service.py

.PHONY: install lint format test build security verify

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	$(PIP) install build ruff bandit pip-audit

lint:
	$(PYTHON) -m ruff check attacks/attack_v19_detector.py tests/test_attack_v19_detector.py

format:
	$(PYTHON) -m ruff format attacks/attack_v19_detector.py tests/test_attack_v19_detector.py

test:
	$(PYTHON) -m pytest tests -q

build:
	$(PYTHON) -m build

security:
	$(PYTHON) -m bandit -r attacks products gateway_server.py spec_service.py -ll
	$(PYTHON) -m pip_audit -r requirements.txt

verify: lint test build security