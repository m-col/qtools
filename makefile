help:
	@echo 'make:                 Display this message'
	@echo 'make clean:           Remove the compiled files (*.pyc, *.pyo)'
	@echo 'make flake8:          Test using flake8'

clean:
	find qtools -regex .\*\.py[co]\$$ -delete
	find qtools -depth -name __pycache__ -type d -exec rm -r -- {} \;

flake8:
	flake8 qtools

.PHONY: default help clean flake8
