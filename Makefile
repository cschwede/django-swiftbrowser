.PHONY  : install run venv

VENV        = venv
SETTINGS    = swiftbrowser.settings

install: venv
	$(VENV)/bin/python setup.py install

run: install
	$(VENV)/bin/django-admin runserver --settings=$(SETTINGS)

venv: $(VENV)/bin/activate
$(VENV)/bin/activate:
	test -d $(VENV) || virtualenv $(VENV)
	$(MAKE) install
	touch $(VENV)/bin/activate
