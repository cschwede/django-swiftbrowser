django-swiftbrowser
===================

[![Build Status](https://travis-ci.org/cschwede/django-swiftbrowser.png?branch=master)](https://travis-ci.org/cschwede/django-swiftbrowser)

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

    django-admin.py startproject myproj
    cd myproj
    cp ~/django-swiftbrowser/example/settings.py myproj/settings.py


3) Adopt myproj/settings.py to your needs, especially settings for Swift and static file directories.

4) Update myproj/urls.py and include swiftbrowser.urls:

    import swiftbrowser.urls

    urlpatterns = patterns('',
        url(r'^', include(swiftbrowser.urls)),
    )

5) Collect static files:

    python manage.py collectstatic

6) Run development server:
    
    python manage.py runserver

   *Important*: Either use 'python manage.py runserver --insecure' or set DEBUG = True in myproj/settings.py if you want to use the
   local development server. Don't use these settings in production!

7) Use 'account:username' to login (or tenant/project:username if using Keystone).

8) Deploying to production? Have a look at Djangos docs: https://docs.djangoproject.com/en/1.5/howto/deployment/wsgi/

9) Please make sure that "tempurl" and "formpost" middlewares are activated in your proxy server. Extract from /etc/swift/proxy-server.conf:

    [pipeline:main]
    pipeline = catch_errors gatekeeper healthcheck proxy-logging cache tempurl formpost tempauth proxy-logging proxy-server

    [filter:tempurl]
    use = egg:swift#tempurl

    [filter:formpost]
    use = egg:swift#formpost


Screenshots
-----------

![Login screen](screenshots/00.png)
![Container view](screenshots/01.png)
![Object view](screenshots/02.png)
