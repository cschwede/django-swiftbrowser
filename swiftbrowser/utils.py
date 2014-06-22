""" Standalone webinterface for Openstack Swift. """
# -*- coding: utf-8 -*-
#pylint:disable=E0611, E1101
import os
import time
import urlparse
import hmac
import logging
import string
import random
from hashlib import sha1

from swiftclient import client

from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib import messages
from django.conf import settings

from PIL import Image
from StringIO import StringIO


logger = logging.getLogger(__name__)


def get_base_url(request):
    base_url = getattr(settings, 'BASE_URL', None)
    if base_url:
        return base_url
    if request.is_secure():
        base_url = "https://%s" % request.get_host()
    else:
        base_url = "http://%s" % request.get_host()
    return base_url


def replace_hyphens(olddict):
    """ Replaces all hyphens in dict keys with an underscore.

    Needed in Django templates to get a value from a dict by key name. """
    newdict = {}
    for key, value in olddict.items():
        key = key.replace('-', '_')
        newdict[key] = value
    return newdict


def prefix_list(prefix):
    prefixes = []

    if prefix:
        elements = prefix.split('/')
        elements = filter(None, elements)
        prefix = ""
        for element in elements:
            prefix += element + '/'
            prefixes.append({'display_name': element, 'full_name': prefix})

    return prefixes


def pseudofolder_object_list(objects, prefix):
    pseudofolders = []
    objs = []

    duplist = []

    for obj in objects:
        # Rackspace Cloudfiles uses application/directory
        # Cyberduck uses application/x-directory
        if obj.get('content_type', None) in ('application/directory',
                                             'application/x-directory'):
            obj['subdir'] = obj['name']

        if 'subdir' in obj:
            # make sure that there is a single slash at the end
            # Cyberduck appends a slash to the name of a pseudofolder
            entry = obj['subdir'].strip('/') + '/'
            if entry != prefix and entry not in duplist:
                duplist.append(entry)
                pseudofolders.append((entry, obj['subdir']))
        else:
            objs.append(obj)

    return (pseudofolders, objs)


def redirect_to_objectview_after_delete(objectname, container):
    if objectname[-1] == '/':  # deleting a pseudofolder, move one level up
            objectname = objectname[:-1]
    prefix = '/'.join(objectname.split('/')[:-1])
    if prefix:
        prefix += '/'
    return redirect("objectview", container=container, prefix=prefix)
    
    
def get_original_account(storage_url, auth_token, container):
    try:
        headers = client.head_container(storage_url, auth_token, container)
        msp = headers.get('x-container-meta-storage-path')
        if msp == None:
            account = storage_url.split('/')[-1]
            original_container_name = container
        else:
            account = msp.split('/')[2]
            original_container_name = '_'.join(container.split('_')[2:])
    except client.ClientException as e:
        logger.error("Cannot head container %s . Error: %s "
                     % (container, str(e)))
        return (None, None)

    return (account, original_container_name)
    

def create_pseudofolder_from_prefix(storage_url, auth_token, container,
                                    prefix, prefixlist):
    #Recursively creates pseudofolders from a given prefix, if the
    #prefix is not included in the prefixlist
    subprefix = '/'.join(prefix.split('/')[0:-1])
    if subprefix == '' or prefix in prefixlist:
        return prefixlist

    prefixlist = create_pseudofolder_from_prefix(storage_url, auth_token,
                                                 container, subprefix,
                                                 prefixlist)

    content_type = 'application/directory'
    obj = None

    client.put_object(storage_url, auth_token,
                          container, prefix + '/', obj,
                          content_type=content_type)
    prefixlist.append(prefix)

    return prefixlist
    
        
def get_temp_key(storage_url, auth_token):
    """ Tries to get meta-temp-url key from account.
    If not set, generate tempurl and save it to acocunt.
    This requires at least account owner rights. """

    try:
        account = client.get_account(storage_url, auth_token)
    except client.ClientException:
        return None

    key = account[0].get('x-account-meta-temp-url-key')

    if not key:
        chars = string.ascii_lowercase + string.digits
        key = ''.join(random.choice(chars) for x in range(32))
        headers = {'x-account-meta-temp-url-key': key}
        try:
            client.post_account(storage_url, auth_token, headers)
        except client.ClientException:
            return None
    return key


def get_temp_url(storage_url, auth_token, container, objectname, expires=600):
    key = get_temp_key(storage_url, auth_token)
    if not key:
        return None

    expires += int(time.time())
    url_parts = urlparse.urlparse(storage_url)
    path = "%s/%s/%s" % (url_parts.path, container, objectname)
    base = "%s://%s" % (url_parts.scheme, url_parts.netloc)
    hmac_body = 'GET\n%s\n%s' % (expires, path)
    sig = hmac.new(key, hmac_body, sha1).hexdigest()
    url = '%s%s?temp_url_sig=%s&temp_url_expires=%s' % (
        base, path, sig, expires)
    return url


def create_thumbnail(request, account, original_container_name, container,
                     objectname):
    """ Creates a thumbnail for an image. """
    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    (thumbnail_storage_url, thumbnail_auth_token) = client.get_auth(
                                    settings.SWIFT_AUTH_URL,
                                    settings.THUMBNAIL_USER,
                                    settings.THUMBNAIL_AUTH_KEY)

    try:
        client.head_container(thumbnail_storage_url, thumbnail_auth_token,
                              account)
    except client.ClientException:
        try:
            client.put_container(thumbnail_storage_url, thumbnail_auth_token,
                             account)
        except client.ClientException as e:
            logger.error("Cannot put container %s. Error: %s "
                         % (container, str(e)))
            return None
    try:
        headers, content = client.get_object(storage_url, auth_token,
                                              container, objectname)
        im = Image.open(StringIO(content))
        im.thumbnail(settings.THUMBNAIL_SIZE, Image.ANTIALIAS)
        output = StringIO()
        mimetype = headers['content-type'].split('/')[-1]
        im.save(output, format=mimetype)
        content = output.getvalue()
        headers = {'X-Delete-After': settings.THUMBNAIL_DURABILITY}
        try:
            client.put_object(thumbnail_storage_url, thumbnail_auth_token,
                    account, "%s_%s" % (original_container_name, objectname),
                    content, headers=headers)
        except client.ClientException as e:
            logger.error("Cannot create thumbnail for image %s."
                         "Could not put thumbnail to storage: %s"
                         % (objectname, str(e)))
        output.close()
    except client.ClientException as e:
        logger.error("Cannot create thumbnail for image %s."
                     "Could not retrieve the image from storage: %s"
                     % (objectname, str(e)))
    except IOError as e:
        logger.error("Cannot create thumbnail for image %s."
                     "An IOError occured: %s" % (objectname, e.strerror))
