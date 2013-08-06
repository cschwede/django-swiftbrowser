django-swiftbrowser
===================

Simple web app build with Django and Twitter Bootstrap to access Openstack Swift.

* No database needed
* Works with keystone, tempauth & swauth
* Support for public containers. ACL support in the works
* Minimal interface, usable on your desktop as well as on your smartphone
* Screenshots anyone? See below!

Quick Install
-------------

1) Install swiftbrowser:

    git clone git://github.com/cschwede/django-swiftbrowser.git
    cd django-swiftbrowser
    sudo python setup.py install

   Optional: run tests

    python runtests.py

2) Create a new Django project:

    django-admin startproject myproj
    cd myproj
    cp ~/django-swiftbrowser/example/settings.py myproj/settings.py


3) Adopt myproj/settings.py to your needs.

4) Run development server:
    
    python manage.py runserver

5) Deploying to production? Have a look at Djangos docs: https://docs.djangoproject.com/en/1.5/howto/deployment/wsgi/

Screenshots
-----------

![Login screen](screenshots/00.png)
![Container view](screenshots/01.png)
![Object view](screenshots/02.png)
