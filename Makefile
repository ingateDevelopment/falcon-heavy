.develop: $(shell find falcon_heavy -type f)
	@pip install -e .
	@touch .develop

test: .develop
	py.test --flake8 --doctest-modules ./tests ./falcon_heavy

vtest: .develop
	py.test --flake8 --doctest-modules ./tests ./falcon_heavy -v

cov: .develop
	py.test --flake8 --doctest-modules --cov falcon_heavy --cov-report html --cov-report term ./tests ./falcon_heavy
	@echo "open file://`pwd`/htmlcov/index.html"

release: ~/.pypirc
	pip install twine
	python setup.py bdist_wheel
	twine upload dist/* --verbose
