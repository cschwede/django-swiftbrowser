FROM python:3

RUN pip install django python-swiftclient uwsgi tox

COPY . /swiftbrowser
WORKDIR /swiftbrowser
RUN python setup.py install

EXPOSE 8000

RUN chown -R nobody /swiftbrowser

USER nobody

CMD ["uwsgi", "--http", ":8000", "--module", "swiftbrowser.wsgi"]
