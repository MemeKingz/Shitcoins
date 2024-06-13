# Scans codebase using flake8. Will return non-zero if any issues are found.
source setup.sh
pip install .[lint]
flake8 --config linting.cfg shitcoins/
