help:
	@echo 'make:                 Display this message'
	@echo 'make clean:           Remove the compiled files (*.pyc, *.pyo)'
	@echo 'make pylint:          Test using pylint'
	@echo 'make flake8:          Test using flake8'

clean:
	find qtools -regex .\*\.py[co]\$$ -delete
	find qtools -depth -name __pycache__ -type d -exec rm -r -- {} \;

TEST_PATHS = \
	qtools

pylint:
	@echo "Running pylint..."
	pylint --rcfile=setup.cfg $(TEST_PATHS)

flake8:
	@echo "Running flake8..."
	flake8 $(TEST_PATHS)

.PHONY: default help clean flake8
