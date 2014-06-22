import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-swiftbrowser',
    version='0.1',
    packages=['swiftbrowser'],
    include_package_data=True,
    license='Apache License (2.0)',
    description='A simple Django app to access Openstack Swift',
    long_description=README,
    url='http://www.cschwede.com/',
    author='Christian Schwede',
    author_email='info@cschwede.de',
    install_requires=['django>=1.5', 'python-swiftclient', 'django-icons-mimetypes>=1.0', 'PIL'],
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache License (2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
