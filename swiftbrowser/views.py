""" Standalone webinterface for Openstack Swift. """
# -*- coding: utf-8 -*-
#pylint:disable=E1101
import os
import time
import urlparse
import hmac
from hashlib import sha1
import logging
import zipfile
from StringIO import StringIO

from swiftclient import client

from django.http import HttpResponse, HttpResponseServerError,\
HttpResponseForbidden
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.contrib import messages
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from swiftbrowser.forms import CreateContainerForm, PseudoFolderForm, \
                               LoginForm, AddACLForm
from swiftbrowser.utils import replace_hyphens, prefix_list, \
                               pseudofolder_object_list, get_temp_key,\
                               get_base_url, get_temp_url, create_thumbnail,\
                               redirect_to_objectview_after_delete,\
                               get_original_account,\
                               create_pseudofolder_from_prefix

import swiftbrowser

logger = logging.getLogger(__name__)


def login(request):
    """ Tries to login user and sets session data """
    request.session.flush()
    form = LoginForm(request.POST or None)
    if form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        try:
            auth_version = settings.SWIFT_AUTH_VERSION or 1
            (storage_url, auth_token) = client.get_auth(
                settings.SWIFT_AUTH_URL, username, password,
                auth_version=auth_version)
            request.session['auth_token'] = auth_token
            request.session['storage_url'] = storage_url
            request.session['username'] = username
            return redirect(containerview)

        except client.ClientException:
            messages.add_message(request, messages.ERROR, _("Login failed."))

    return render_to_response('login.html', {'form': form, },
                              context_instance=RequestContext(request))


def containerview(request):
    """ Returns a list of all containers in current account. """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    try:
        account_stat, containers = client.get_account(storage_url, auth_token)
    except client.ClientException:
        return redirect(login)

    account_stat = replace_hyphens(account_stat)

    account = storage_url.split('/')[-1]
    
    return render_to_response('containerview.html', {
        'account': account,
        'account_stat': account_stat,
        'containers': containers,
        'session': request.session,
    }, context_instance=RequestContext(request))


def create_container(request):
    """ Creates a container (empty object of type application/directory) """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    form = CreateContainerForm(request.POST or None)
    if form.is_valid():
        container = form.cleaned_data['containername']
        try:
            client.put_container(storage_url, auth_token, container)
            messages.add_message(request, messages.INFO,
                                 _("Container created."))
        except client.ClientException:
            messages.add_message(request, messages.ERROR, _("Access denied."))

        return redirect(containerview)

    return render_to_response('create_container.html', {
                              }, context_instance=RequestContext(request))


def delete_container(request, container):
    """ Deletes a container """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    try:
        _m, objects = client.get_container(storage_url, auth_token, container)
        for obj in objects:
            client.delete_object(storage_url, auth_token,
                                 container, obj['name'])
        client.delete_container(storage_url, auth_token, container)
        messages.add_message(request, messages.INFO, _("Container deleted."))
    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))

    return redirect(containerview)


def objectview(request, container, prefix=None):
    """ Returns list of all objects in current container. """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    try:
        meta, objects = client.get_container(storage_url, auth_token,
                                             container, delimiter='/',
                                             prefix=prefix)

    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    prefixes = prefix_list(prefix)
    pseudofolders, objs = pseudofolder_object_list(objects, prefix)
    base_url = get_base_url(request)
    account = storage_url.split('/')[-1]

    read_acl = meta.get('x-container-read', '').split(',')
    public = False
    required_acl = ['.r:*', '.rlistings']
    if [x for x in read_acl if x in required_acl]:
        public = True

    return render_to_response("objectview.html", {
        'container': container,
        'objects': objs,
        'folders': pseudofolders,
        'session': request.session,
        'prefix': prefix,
        'prefixes': prefixes,
        'base_url': base_url,
        'account': account,
        'public': public,
        },
        context_instance=RequestContext(request))


def upload(request, container, prefix=None):
    """ Display upload form using swift formpost """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    redirect_url = get_base_url(request)
    redirect_url += reverse('objectview', kwargs={'container': container, })

    swift_url = storage_url + '/' + container + '/'
    if prefix:
        swift_url += prefix
        redirect_url += prefix

    url_parts = urlparse.urlparse(swift_url)
    path = url_parts.path

    max_file_size = 5 * 1024 * 1024 * 1024
    max_file_count = 1
    expires = int(time.time() + 15 * 60)
    key = get_temp_key(storage_url, auth_token)
    if not key:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        if prefix:
            return redirect(objectview, container=container, prefix=prefix)
        else:
            return redirect(objectview, container=container)

    hmac_body = '%s\n%s\n%s\n%s\n%s' % (path, redirect_url,
        max_file_size, max_file_count, expires)
    signature = hmac.new(key, hmac_body, sha1).hexdigest()

    prefixes = prefix_list(prefix)

    return render_to_response('upload_form.html', {
                              'swift_url': swift_url,
                              'redirect_url': redirect_url,
                              'max_file_size': max_file_size,
                              'max_file_count': max_file_count,
                              'expires': expires,
                              'signature': signature,
                              'container': container,
                              'prefix': prefix,
                              'prefixes': prefixes,
                              }, context_instance=RequestContext(request))


def download(request, container, objectname):
    """ Download an object from Swift """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')
    url = swiftbrowser.utils.get_temp_url(storage_url, auth_token,
                                          container, objectname)
    if not url:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(objectview, container=container)

    return redirect(url)


def download_collection(request, container, prefix=None, non_recursive=False):
    """ Download the content of an entire container/pseudofolder
    as a Zip file. """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    delimiter = '/' if non_recursive else None
    try:
        x, objects = client.get_container(storage_url, auth_token,
                                         container, delimiter=delimiter,
                                         prefix=prefix)
    except client.ClientException:
        return HttpResponseForbidden()

    x, objs = pseudofolder_object_list(objects, prefix)

    output = StringIO()
    zipf = zipfile.ZipFile(output, 'w')
    for o in objs:
        name = o['name']
        try:
            x, content = client.get_object(storage_url, auth_token, container,
                                           name)
        except client.ClientException:
            return HttpResponseForbidden()

        if prefix:
            name = name[len(prefix):]
        zipf.writestr(name, content)
    zipf.close()

    if prefix:
        filename = prefix.split('/')[-2]
    else:
        filename = container
    response = HttpResponse(output.getvalue(), 'application/zip')
    response['Content-Disposition'] = 'attachment; filename="%s.zip"'\
    % (filename)
    output.close()
    return response
    
    
def delete_object(request, container, objectname):
    """ Deletes an object """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')
    try:
        headers = client.head_object(storage_url, auth_token, container,
                                      objectname)
        if headers.get('content-type', '') == 'application/directory':
            #retrieve list of all subdirs
            x, objects = client.get_container(storage_url, auth_token,
                                              container, prefix=objectname)
            for o in objects:
                name = o['name']
                client.delete_object(storage_url, auth_token, container, name)
            messages.add_message(request, messages.INFO, _("Folder deleted."))
        else:
            client.delete_object(storage_url, auth_token, container,
                                 objectname)
            messages.add_message(request, messages.INFO, _("Object deleted."))
    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))
    if objectname[-1] == '/':  # deleting a pseudofolder, move one level up
        objectname = objectname[:-1]
    prefix = '/'.join(objectname.split('/')[:-1])
    if prefix:
        prefix += '/'
    return redirect(objectview, container=container, prefix=prefix)


def toggle_public(request, container):
    """ Sets/unsets '.r:*,.rlistings' container read ACL """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    try:
        meta = client.head_container(storage_url, auth_token, container)
    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    read_acl = meta.get('x-container-read', '')
    if '.rlistings' and '.r:*' in read_acl:
        read_acl = read_acl.replace('.r:*', '')
        read_acl = read_acl.replace('.rlistings', '')
        read_acl = read_acl.replace(',,', ',')
    else:
        read_acl += '.r:*,.rlistings'
    headers = {'X-Container-Read': read_acl, }

    try:
        client.post_container(storage_url, auth_token, container, headers)
    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))

    return redirect(objectview, container=container)


def public_objectview(request, account, container, prefix=None):
    """ Returns list of all objects in current container. """
    storage_url = settings.STORAGE_URL + account
    auth_token = ' '
    try:
        _meta, objects = client.get_container(storage_url, auth_token,
                                             container, delimiter='/',
                                             prefix=prefix)

    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    prefixes = prefix_list(prefix)
    pseudofolders, objs = pseudofolder_object_list(objects, prefix)
    base_url = get_base_url(request)
    account = storage_url.split('/')[-1]

    return render_to_response("publicview.html", {
        'container': container,
        'objects': objs,
        'folders': pseudofolders,
        'prefix': prefix,
        'prefixes': prefixes,
        'base_url': base_url,
        'storage_url': storage_url,
        'account': account,
        },
        context_instance=RequestContext(request))


def tempurl(request, container, objectname):
    """ Displays a temporary URL for a given container object """

    container = unicode(container).encode('utf-8')
    objectname = unicode(objectname).encode('utf-8')

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    url = get_temp_url(storage_url, auth_token,
                       container, objectname, 7 * 24 * 3600)

    if not url:
        return HttpResponseForbidden()

    return HttpResponse(url, content_type="text/plain")


def create_pseudofolder(request, container, prefix=None):
    """ Creates a pseudofolder (empty object of type application/directory) """
    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    form = PseudoFolderForm(request.POST)
    if form.is_valid():
        foldername = request.POST.get('foldername', None)
        if prefix:
            foldername = prefix + '/' + foldername
        foldername = os.path.normpath(foldername)
        foldername = foldername.strip('/')
        foldername += '/'

        content_type = 'application/directory'
        obj = None

        try:
            client.put_object(storage_url, auth_token,
                              container, foldername, obj,
                              content_type=content_type)
            messages.add_message(request, messages.INFO,
                                 _("Pseudofolder created."))
        except client.ClientException:
            messages.add_message(request, messages.ERROR, _("Access denied."))

        if prefix:
            return redirect(objectview, container=container, prefix=prefix)
        return redirect(objectview, container=container)

    return render_to_response('create_pseudofolder.html', {
                              'container': container,
                              'prefix': prefix,
                              }, context_instance=RequestContext(request))


def get_acls(storage_url, auth_token, container):
    """ Returns ACLs of given container. """
    cont = client.head_container(storage_url, auth_token, container)
    readers = cont.get('x-container-read', '')
    writers = cont.get('x-container-write', '')
    return (readers, writers)


def remove_duplicates_from_acl(acls):
    """ Removes possible duplicates from a comma-separated list. """
    entries = acls.split(',')
    cleaned_entries = list(set(entries))
    acls = ','.join(cleaned_entries)
    return acls


def edit_acl(request, container):
    """ Edit ACLs on given container. """

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    if request.method == 'POST':
        form = AddACLForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']

            try:
                (readers, writers) = get_acls(storage_url,
                    auth_token, container)
            except KeyError:
                return redirect(logout)

            readers = remove_duplicates_from_acl(readers)
            writers = remove_duplicates_from_acl(writers)

            if form.cleaned_data['read']:
                readers += ",%s" % username

            if form.cleaned_data['write']:
                writers += ",%s" % username

            headers = {'X-Container-Read': readers,
                       'X-Container-Write': writers}
            try:
                client.post_container(storage_url,
                    auth_token, container, headers)
                message = "ACLs updated."
                messages.add_message(request, messages.INFO, message)
            except client.ClientException:
                message = "ACL update failed"
                messages.add_message(request, messages.ERROR, message)

    if request.method == 'GET':
        delete = request.GET.get('delete', None)
        if delete:
            users = delete.split(',')

            (readers, writers) = get_acls(storage_url, auth_token, container)

            new_readers = ""
            for element in readers.split(','):
                if element not in users:
                    new_readers += element
                    new_readers += ","

            new_writers = ""
            for element in writers.split(','):
                if element not in users:
                    new_writers += element
                    new_writers += ","

            headers = {'X-Container-Read': new_readers,
                       'X-Container-Write': new_writers}
            try:
                client.post_container(storage_url, auth_token,
                                      container, headers)
                message = "ACL removed."
                messages.add_message(request, messages.INFO, message)
            except client.ClientException:
                message = "ACL update failed."
                messages.add_message(request, messages.ERROR, message)

    (readers, writers) = get_acls(storage_url, auth_token, container)

    acls = {}

    if readers != "":
        readers = remove_duplicates_from_acl(readers)
        for entry in readers.split(','):
            acls[entry] = {}
            acls[entry]['read'] = True
            acls[entry]['write'] = False

    if writers != "":
        writers = remove_duplicates_from_acl(writers)
        for entry in writers.split(','):
            if entry not in acls:
                acls[entry] = {}
                acls[entry]['read'] = False
            acls[entry]['write'] = True

    public = False
    if acls.get('.r:*', False) and acls.get('.rlistings', False):
        public = True

    if request.is_secure():
        base_url = "https://%s" % request.get_host()
    else:
        base_url = "http://%s" % request.get_host()

    return render_to_response('edit_acl.html', {
        'container': container,
        'account': storage_url.split('/')[-1],
        'session': request.session,
        'acls': acls,
        'public': public,
        'base_url': base_url,
    }, context_instance=RequestContext(request))


def serve_thumbnail(request, container, objectname):
    if request.session.get('username', '') == settings.THUMBNAIL_USER:
        return HttpResponseForbidden()

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    try:
        im_headers = client.head_object(storage_url, auth_token, container,
                                    objectname)
        im_ts = float(im_headers['x-timestamp'])
    except client.ClientException as e:
        logger.error("Cannot head object %s of container %s. Error: %s "
                     % (objectname, container, str(e)))
        return HttpResponseServerError()

    #Is this an alias container? Then use the original account
    #to prevent duplicating
    (account, original_container_name) = get_original_account(
                                        storage_url, auth_token, container)
    if account is None:
        return HttpResponseServerError()

    (thumbnail_storage_url, thumbnail_auth_token) = client.get_auth(
            settings.SWIFT_AUTH_URL, settings.THUMBNAIL_USER,
            settings.THUMBNAIL_AUTH_KEY)
    try:
        th_headers = client.head_object(thumbnail_storage_url,
                                        thumbnail_auth_token, account,
                                        "%s_%s" % (original_container_name,
                                        objectname))
        th_ts = float(th_headers['x-timestamp'])
        if th_ts < im_ts:
            create_thumbnail(request, account, original_container_name,
                             container, objectname)
    except client.ClientException:
        create_thumbnail(request, account, original_container_name,
                         container, objectname)
    th_name = "%s_%s" % (original_container_name, objectname)
    try:
        headers, image_data = client.get_object(thumbnail_storage_url,
                        thumbnail_auth_token, account, th_name)
    except client.ClientException as e:
        logger.error("Cannot get object %s of container %s. Error: %s "
                     % (th_name, account, str(e)))
        return HttpResponseServerError()

    return HttpResponse(image_data, mimetype=headers['content-type'])


def trashview(request, account):
    storage_url = request.session.get('storage_url', '')

    #Users are only allowed to view the trash of their own account.
    if storage_url == '' or account != storage_url.split('/')[-1]:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    (trash_storage_url, trash_auth_token) = client.get_auth(
                            settings.SWIFT_AUTH_URL,
                            settings.TRASH_USER, settings.TRASH_AUTH_KEY)

    try:
        client.head_container(trash_storage_url, trash_auth_token, account)
    except client.ClientException:
        try:
            client.put_container(trash_storage_url, trash_auth_token, account)
        except client.ClientException as e:
            logger.error("Cannot put container %s. Error: %s "
                     % (account, str(e)))
            messages.add_message(request, messages.ERROR, _("Internal error."))
            return redirect(containerview)

    objs = []
    try:
        x, objects = client.get_container(trash_storage_url,
                                             trash_auth_token, account)
        for o in objects:
            last_modified = o['last_modified']
            size = 0
            directory = False
            try:
                headers = client.head_object(trash_storage_url,
                                             trash_auth_token,
                                             account, o['name'])
                size = headers.get('x-object-meta-original-length', 0)
                if headers.get('content-type', '') == 'application/directory':
                    directory = True
            except client.ClientException:
                pass

            obj = {'name': o['name'], 'size': size,
                   'last_modified': last_modified, 'dir': directory}
            objs.append(obj)
    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    return render_to_response("trashview.html", {
        'objects': objs,
        'session': request.session,
        'account': account,
        },
        context_instance=RequestContext(request))


def delete_trash(request, account, trashname):
    storage_url = request.session.get('storage_url', '')

    if storage_url == '' or account != storage_url.split('/')[-1]:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    (trash_storage_url, trash_auth_token) = client.get_auth(
                            settings.SWIFT_AUTH_URL,
                            settings.TRASH_USER, settings.TRASH_AUTH_KEY)

    try:
        client.delete_object(trash_storage_url, trash_auth_token,
                             account, trashname)
        messages.add_message(request, messages.INFO, _("Object deleted."))
    except client.ClientException:
        messages.add_message(request, messages.ERROR, _("Access denied."))

    return redirect(trashview, account=account)


def restore_trash(request, account, trashname):
    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    if storage_url == '' or account != storage_url.split('/')[-1]:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    (trash_storage_url, trash_auth_token) = client.get_auth(
                            settings.SWIFT_AUTH_URL,
                            settings.TRASH_USER, settings.TRASH_AUTH_KEY)
    try:
        x, zipped_content = client.get_object(trash_storage_url,
                                                 trash_auth_token,
                                                 account, trashname)
    except client.ClientException as e:
        logger.error("Cannot retrieve object %s of container %s. Error: %s "
                     % (trashname, account, str(e)))
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return redirect(trashview, account=account)

    container = trashname.split('/')[0]
    objectname = '/'.join(trashname.split('/')[1:])
    inp = StringIO(zipped_content)
    zipf = zipfile.ZipFile(inp, 'r')
    content = zipf.read(objectname)
    zipf.close()

    try:
        client.put_object(storage_url, auth_token, container, objectname,
                          content)
    except client.ClientException as e:
        logger.error("Cannot put object %s to container %s. Error: %s "
                     % (objectname, container, str(e)))
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return redirect(trashview, account=account)

    messages.add_message(request, messages.INFO, _("Object restored."))
    try:
        client.delete_object(trash_storage_url, trash_auth_token,
                             account, trashname)
    except client.ClientException as e:
        logger.error("Cannot delete object %s of container %s. Error: %s"
                     % (trashname, account, str(e)))

    return redirect(trashview, account=account)


def restore_trash_collection(request, account, trashname):
    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    if account != storage_url.split('/')[-1]:
        messages.add_message(request, messages.ERROR, _("Access denied."))
        return redirect(containerview)

    (trash_storage_url, trash_auth_token) = client.get_auth(
                            settings.SWIFT_AUTH_URL,
                            settings.TRASH_USER, settings.TRASH_AUTH_KEY)
    try:
        x, zipped_content = client.get_object(trash_storage_url,
                                                 trash_auth_token,
                                                 account, trashname)
    except client.ClientException as e:
        logger.error("Cannot retrieve object %s of container %s. Error: %s "
                     % (trashname, account, str(e)))
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return redirect(trashview, account=account)

    container = trashname.split('/')[0]
    directory = True
    try:
        client.head_container(storage_url, auth_token, container)
    except client.ClientException:
        try:
            client.put_container(storage_url, auth_token, container)
            directory = False
        except client.ClientException as e:
            logger.error("Cannot put container %s. Error: %s "
                         % (container, str(e)))
            messages.add_message(request, messages.ERROR, _("Internal error."))
            return redirect(trashview, account=account)

    inp = StringIO(zipped_content)
    zipf = zipfile.ZipFile(inp, 'r')
    prefixlist = []
    for name in zipf.namelist():
        try:
            prefix = '/'.join(name.split('/')[0:-1])
            prefixlist = create_pseudofolder_from_prefix(storage_url,
                                                    auth_token, container,
                                                    prefix, prefixlist)
        except client.ClientException as e:
            logger.error("Cannot create pseudofolder from prefix %s in "
            "container %s. Error: %s " % (prefix, container, str(e)))

        content = zipf.read(name)
        try:
            client.put_object(storage_url, auth_token, container, name,
                              content)
        except client.ClientException as e:
            logger.error("Cannot put object %s to container %s. Error: %s "
                     % (name, container, str(e)))
            messages.add_message(request, messages.ERROR, _("Internal error."))
    zipf.close()

    msg = "%s restored." % ("Folder" if directory else "Container")
    messages.add_message(request, messages.INFO, _(msg))
    try:
        client.delete_object(trash_storage_url, trash_auth_token,
                             account, trashname)
    except client.ClientException as e:
        logger.error("Cannot delete object %s of container %s. Error: %s"
                     % (trashname, account, str(e)))
    return redirect(trashview, account=account)


def move_to_trash(request, container, objectname):
    if request.session.get('username', '') == settings.TRASH_USER:
        return HttpResponseForbidden()

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    #Is this an alias container? Then use the original account
    #to prevent duplicating.
    (account, original_container_name) = get_original_account(
                                        storage_url, auth_token, container)
    if account is None:
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return redirect_to_objectview_after_delete(objectname, container)

    (trash_storage_url, trash_auth_token) = client.get_auth(
                            settings.SWIFT_AUTH_URL,
                            settings.TRASH_USER, settings.TRASH_AUTH_KEY)
    try:
        meta, content = client.get_object(storage_url, auth_token, container,
                                       objectname)

    except client.ClientException as e:
        logger.error("Cannot retrieve object %s of container %s. Error: %s"
                     % (objectname, container, str(e)))
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return redirect_to_objectview_after_delete(objectname, container)

    try:
        client.head_container(trash_storage_url, trash_auth_token, account)
    except client.ClientException:
        try:
            client.put_container(trash_storage_url, trash_auth_token, account)
        except client.ClientException as e:
            logger.error("Cannot put container %s. Error: %s "
                         % (container, str(e)))
            messages.add_message(request, messages.ERROR, _("Internal error."))
            return redirect_to_objectview_after_delete(objectname, container)

    output = StringIO()
    zipf = zipfile.ZipFile(output, 'w')
    zipf.writestr(objectname, content)
    zipf.close()

    trashname = "%s/%s" % (original_container_name, objectname)
    try:
        headers = {'X-Delete-After': settings.TRASH_DURABILITY,
                   'x-object-meta-original-length': meta['content-length']}
        client.put_object(trash_storage_url, trash_auth_token,
                   account, trashname, contents=output.getvalue(),
                   headers=headers)
        output.close()
    except client.ClientException as e:
        logger.error("Cannot put object %s to container %s. Error: %s "
                     % (trashname, container, str(e)))
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return redirect_to_objectview_after_delete(objectname, container)

    try:
        client.delete_object(storage_url, auth_token, container, objectname)
    except client.ClientException as e:
        logger.error("Cannot delete object %s of container %s. Error: %s "
                     % (container, objectname, str(e)))
        messages.add_message(request, messages.ERROR, _("Access denied."))

        try:
            client.delete_object(trash_storage_url, trash_auth_token,
                                 account, trashname)
        except client.ClientException:
            pass
        return redirect_to_objectview_after_delete(objectname, container)

    msg = "%s moved to trash." % trashname
    messages.add_message(request, messages.INFO, _(msg))
    return redirect_to_objectview_after_delete(objectname, container)


def move_collection_to_trash(request, container, prefix):
    if request.session['username'] == settings.TRASH_USER:
        return HttpResponseForbidden()

    storage_url = request.session.get('storage_url', '')
    auth_token = request.session.get('auth_token', '')

    #Is this an alias container? Then use the original account
    #to prevent duplicating.
    (account, original_container_name) = get_original_account(
                                        storage_url, auth_token, container)
    if account is None:
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return (redirect(containerview) if prefix is None else
            redirect_to_objectview_after_delete(prefix, container))

    (trash_storage_url, trash_auth_token) = client.get_auth(
                            settings.SWIFT_AUTH_URL,
                            settings.TRASH_USER, settings.TRASH_AUTH_KEY)

    try:
        x, objects = client.get_container(storage_url, auth_token,
                                         container, prefix=prefix)
    except client.ClientException as e:
        if prefix is None:
            logger.error("Cannot retrieve container %s."
             "Error: %s " % (container, str(e)))
        else:
            logger.error("Cannot retrieve container %s with prefix %s."
                         "Error: %s " % (container, prefix, str(e)))

        messages.add_message(request, messages.ERROR, _("Internal error."))
        return (redirect(containerview) if prefix is None else
            redirect_to_objectview_after_delete(prefix, container))

    x, objs = pseudofolder_object_list(objects, prefix)

    output = StringIO()
    zipf = zipfile.ZipFile(output, 'w')
    original_length = 0
    for o in objs:
        name = o['name']
        try:
            meta, content = client.get_object(storage_url, auth_token,
                                              container, name)
            original_length += int(meta.get('content-length', 0))
        except client.ClientException as e:
            logger.error("Cannot retrieve object %s of container %s. Error: %s"
                     % (name, container, str(e)))
            messages.add_message(request, messages.ERROR, _("Internal error."))
            return (redirect(containerview) if prefix is None else
                redirect_to_objectview_after_delete(prefix, container))

        zipf.writestr(name, content)
    zipf.close()

    try:
        client.head_container(trash_storage_url, trash_auth_token, account)
    except client.ClientException:
        try:
            client.put_container(trash_storage_url, trash_auth_token, account)
        except client.ClientException as e:
            logger.error("Cannot put container %s. Error: %s "
                         % (container, str(e)))
            messages.add_message(request, messages.ERROR, _("Internal error."))
            return (redirect(containerview) if prefix is None else
                redirect_to_objectview_after_delete(prefix, container))

    trashname = "%s/%s" % (original_container_name,
                           '' if prefix is None else prefix)
    try:
        headers = {'X-Delete-After': settings.TRASH_DURABILITY,
                   'x-object-meta-original-length': str(original_length)}
        client.put_object(trash_storage_url, trash_auth_token,
                   account, trashname, output.getvalue(),
                   content_type='application/directory', headers=headers)
        output.close()
    except client.ClientException as e:
        logger.error("Cannot put object %s to container %s. Error: %s "
                     % (trashname, container, str(e)))
        messages.add_message(request, messages.ERROR, _("Internal error."))
        return (redirect(containerview) if prefix is None else
            redirect_to_objectview_after_delete(prefix, container))

    try:
        for o in objects:
            name = o['name']
            client.delete_object(storage_url, auth_token, container, name)
    except client.ClientException as e:
        logger.error("Cannot delete all objects of container %s."
                         "Error: %s " % (container, str(e)))
        messages.add_message(request, messages.ERROR, _("Access denied."))

        try:
            client.delete_object(trash_storage_url, trash_auth_token,
                                 account, trashname)
        except client.ClientException:
            pass

        return (redirect(containerview) if prefix is None else
            redirect_to_objectview_after_delete(prefix, container))

    if prefix is None:
        try:
            client.delete_container(storage_url, auth_token, container)
        except client.ClientException as e:
            logger.error("Cannot delete container %s."
                         "Error: %s " % (container, str(e)))
            messages.add_message(request, messages.ERROR, _("Access denied."))

            try:
                client.delete_object(trash_storage_url, trash_auth_token,
                                     account, trashname)
            except client.ClientException:
                pass

            return redirect(containerview)

    msg = "%s moved to trash." % ("Container" if prefix is None else "Folder")
    messages.add_message(request, messages.INFO, _(msg))
    return (redirect(containerview) if prefix is None else
            redirect_to_objectview_after_delete(prefix, container))
