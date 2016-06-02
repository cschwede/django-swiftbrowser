.PHONY  : all clean install run venv

VENV        = venv
SETTINGS    = swiftbrowser.settings
ADDRPORT    = '127.0.0.1:8000'

all: install

install: venv
	$(VENV)/bin/python setup.py install

run: install
	$(VENV)/bin/django-admin runserver --settings=$(SETTINGS) $(ADDRPORT)

clean:
	rm -rf $(VENV) build dist *.egg-info

venv: $(VENV)/bin/activate
$(VENV)/bin/activate:
	test -d $(VENV) || virtualenv $(VENV)
	$(MAKE) install
	touch $(VENV)/bin/activate
