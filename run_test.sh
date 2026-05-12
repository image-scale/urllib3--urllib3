#!/bin/bash
set -eo pipefail
cd "$(dirname "$0")"
PYTHONPATH=src python -m pytest tests/ --tb=short -q --no-header -rN
