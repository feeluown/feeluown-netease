.PHONY: docs

all: test

lint:
	flake8 fuo_netease/

unittest: pytest

pytest:
	pytest --cov-report= --cov=fuo_netease

test: lint unittest

clean:
	find . -name "*~" -exec rm -f {} \;
	find . -name "*.pyc" -exec rm -f {} \;
	find . -name "*flymake.py" -exec rm -f {} \;
	find . -name "\#*.py\#" -exec rm -f {} \;
	find . -name ".\#*.py\#" -exec rm -f {} \;
	find . -name __pycache__ -delete
