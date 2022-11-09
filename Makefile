.PHONY: run
run:
	pipenv run sortingshop

.PHONY: setup
setup:
	pipenv install

.PHONY: build
build:
	rm -rf dist
	pipenv run python -m build

.PHONY: upload
upload:
	pipenv run python -m twine upload dist/*
