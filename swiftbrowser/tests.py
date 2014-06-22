#!/usr/bin/python
# -*- coding: utf8 -*-
#pylint:disable=E1103
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
import random
import swiftbrowser
import swiftclient
import mock
import zipfile


class MockTest(TestCase):
    """ Unit tests for swiftbrowser

    All calls using python-swiftclient.clients are replaced using mock """

    def test_container_view(self):
        swiftclient.client.get_auth = mock.Mock(return_value=('storage_url',
                                                              'auth_token'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_account = mock.Mock(return_value=[{}, []],
            side_effect=swiftclient.client.ClientException(''))

        resp = self.client.get(reverse('containerview'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('login'))

        swiftclient.client.get_account = mock.Mock(return_value=[{}, []])

        resp = self.client.get(reverse('containerview'))
        self.assertEqual(resp.context['containers'], [])

    def test_create_container(self):
        swiftclient.client.put_container = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))

        resp = self.client.post(reverse('create_container'),
                                {'containername': 'container'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

        swiftclient.client.put_container = mock.Mock()

        resp = self.client.get(reverse('create_container'))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(reverse('create_container'),
                                {'containername': 'container'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

    def test_delete_container(self):
        objects = [{'name': 'obj1'}, {'name': 'obj2'}]
        swiftclient.client.get_container = mock.Mock(
            return_value=({}, objects))

        swiftclient.client.delete_object = mock.Mock()
        swiftclient.client.delete_container = mock.Mock()
        resp = self.client.post(reverse('delete_container',
                                kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

        expected = [mock.call('', '', 'container', 'obj1'),
                    mock.call('', '', 'container', 'obj2')]
        self.assertEqual(swiftclient.client.delete_object.call_args_list,
                         expected)

        swiftclient.client.delete_container = mock.Mock()

        resp = self.client.post(reverse('delete_container',
                                kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

    def test_objectview(self):
        swiftclient.client.get_auth = mock.Mock(return_value=('storage_url',
                                                              'auth_token'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_container = mock.Mock(return_value=[{}, []],
            side_effect=swiftclient.client.ClientException(''))

        resp = self.client.get(reverse('objectview',
                               kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

        meta = {}
        objects = [{'subdir': 'pre'}, {'name': 'pre/fix'}]
        swiftclient.client.get_container = mock.Mock(
            return_value=(meta, objects))

        resp = self.client.get(reverse('objectview',
                               kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['folders'], [('pre/', 'pre')])

        resp = self.client.get(reverse('objectview',
                               kwargs={'container': 'container',
                                       'prefix': 'pre/'}))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['folders'], [])
        self.assertEqual(resp.context['prefix'], 'pre/')

    def test_upload_form(self):
        swiftclient.client.get_container = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        swiftclient.client.post_account = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))

        account = [{}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))

        resp = self.client.get(reverse('upload',
                               kwargs={'container': 'container'}))
        self.assertEqual(resp['Location'],
                         'http://testserver/objects/container/')

        account = [{'x-account-meta-temp-url-key': 'dummy'}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))

        resp = self.client.get(reverse('upload',
                               kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 200)

    def test_download(self):
        with mock.patch('swiftbrowser.utils.get_temp_url',
                   mock.Mock(return_value="http://url")):

            resp = self.client.get(reverse('download', kwargs={
                                        'container': 'container',
                                        'objectname': 'testfile'}))

            self.assertEqual(resp['Location'], "http://url")

        with mock.patch('swiftbrowser.views.get_temp_url',
                        mock.Mock(return_value=None)):
            resp = self.client.get(reverse('download', kwargs={
                                        'container': 'container',
                                        'objectname': 'testfile'}))
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp['Location'],
                         'http://testserver/objects/container/')

    def test_replace_hyphens(self):
        old = {'test-key': 'test-value'}
        new = swiftbrowser.utils.replace_hyphens(old)
        self.assertEqual(new, {'test_key': 'test-value'})

    def test_login(self):
        data = ("auth_token_dummy", "storage_url_dummy")
        swiftclient.client.get_auth = mock.Mock(return_value=data)
        resp = self.client.post(reverse('login'), {
            'username': 'test:tester',
            'password': 'testing'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

        swiftclient.client.get_auth = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        resp = self.client.post(reverse('login'), {
            'username': 'wrong:user',
            'password': 'invalid'})
        self.assertContains(resp, "Login failed")

        resp = self.client.get(reverse('login'))
        self.assertTemplateUsed(resp, 'login.html')

    def test_delete(self):
        swiftclient.client.head_object = mock.Mock()
        swiftclient.client.delete_object = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(reverse('delete_object', kwargs={
                                        'container': 'container',
                                        'objectname': 'testfile'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver/objects/container/')

        swiftclient.client.delete_object = mock.Mock()
        resp = self.client.get(reverse('delete_object', kwargs={
                                       'container': 'container',
                                       'objectname': 'testfile'}))
        self.assertEqual(resp.status_code, 302)

    def test_toggle_public(self):
        swiftclient.client.head_container = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        response = self.client.get(reverse('toggle_public',
                                           kwargs={'container': 'container'}))
        self.assertEqual(response.status_code, 302)

        swiftclient.client.head_container = mock.Mock(
            return_value={'x-container-read': ''})
        swiftclient.client.post_container = mock.Mock()

        response = self.client.get(reverse('toggle_public',
                                           kwargs={'container': 'container'}))
        self.assertEqual(response.status_code, 302)

        swiftclient.client.post_container.assert_called_with('', '',
            'container', {'X-Container-Read': '.r:*,.rlistings'})

        swiftclient.client.head_container = mock.Mock(return_value={
            'x-container-read': 'x,.r:*,.rlistings'})
        response = self.client.get(reverse('toggle_public',
                                           kwargs={'container': 'container'}))
        self.assertEqual(response.status_code, 302)

        swiftclient.client.post_container.assert_called_with('', '',
            'container', {'X-Container-Read': 'x,'})

    def test_public_objectview(self):
        swiftclient.client.get_container = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(reverse('public_objectview',
                               kwargs={'account': 'AUTH_test',
                                       'container': 'container',
                                       }))

        self.assertEqual(resp.status_code, 302)

        objects = [{'name': 'testfile'},
                   {'subdir': 'pre'},
                   {'name': 'pre/fix'}]
        swiftclient.client.get_container = mock.Mock(
            return_value=({}, objects))

        resp = self.client.get(reverse('public_objectview',
                               kwargs={'account': "dummy",
                                       'container': 'container',
                                       }))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['folders'], [('pre/', 'pre')])

        resp = self.client.get(reverse('public_objectview',
                               kwargs={'account': "dummy",
                                       'container': 'container',
                                       'prefix': 'pre/',
                                       }))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['folders'], [])
        self.assertEqual(resp.context['prefix'], 'pre/')

    def test_get_temp_key(self):

        # Unauthorized request
        swiftclient.client.get_container = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        self.assertIsNone(swiftbrowser.utils.get_temp_key("dummy", ''))

        # Authorized, no temp url key set
        account = [{}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))
        swiftclient.client.post_account = mock.Mock()
        random.choice = mock.Mock(return_value="a")

        self.assertIsNotNone(swiftbrowser.utils.get_temp_key("dummy", "dummy"))
        swiftclient.client.post_account.assert_called_with('dummy', 'dummy',
            {'x-account-meta-temp-url-key': 'a' * 32})

        # Authorized, temp url key already set
        account = [{'x-account-meta-temp-url-key': 'dummy'}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))
        self.assertIsNotNone(swiftbrowser.utils.get_temp_key("dummy", "dummy"))

    def test_tempurl(self):
        swiftclient.client.get_account = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        response = self.client.get(reverse('tempurl', args=['c', 'o']))
        self.assertEqual(response.status_code, 403)

        account = [{'x-account-meta-temp-url-key': 'dummy'}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))
        response = self.client.get(reverse('tempurl', args=['c', 'o']))
        self.assertEqual(response.status_code, 200)

        with mock.patch('swiftbrowser.views.get_temp_url',
                         mock.Mock(return_value='http://url')):
            resp = self.client.get(reverse('tempurl', args=['c', 'o']))
            self.assertEqual(resp.content, 'http://url')

    def test_create_pseudofolder(self):
        swiftclient.client.put_object = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))

        swiftclient.client.put_container('storage_url',
                                         'auth_token',
                                         'container')

        resp = self.client.post(reverse('create_pseudofolder',
                                        kwargs={'container': 'container'}),
                                        {'foldername': 'test'})
        self.assertEqual(resp.status_code, 302)

        swiftclient.client.put_object.assert_called_with('', '', u'container',
            u'test/', None, content_type='application/directory')

        resp = self.client.post(reverse('create_pseudofolder',
                                        kwargs={'container': 'container',
                                                'prefix': 'prefix'}),
                                        {'foldername': 'test2'})
        self.assertEqual(resp.status_code, 302)

    def test_edit_acl(self):
        swiftclient.client.head_container = mock.Mock(return_value={})

        swiftclient.client.post_container = mock.Mock()

        resp = self.client.post(reverse('edit_acl',
                                kwargs={'container': 'container'}),
                                {'username': 'testuser',
                                 'read': 'On',
                                 'write': 'On'})
        self.assertEqual(resp.status_code, 200)
        swiftclient.client.post_container.assert_called_with('', '',
            'container', {'X-Container-Read': ',testuser',
                          'X-Container-Write': ',testuser'})

    def test_trash(self):
        # following views only accessible for account-owners
        swiftclient.client.get_auth = mock.Mock(return_value=('/account',
                                                              'a'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        resp = self.client.get(reverse('trashview',
                                       kwargs={'account': 'other_account'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('containerview'))

        resp = self.client.get(reverse('delete_trash',
                                       kwargs={'account': 'other_account',
                                               'trashname': 't'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('containerview'))

        resp = self.client.get(reverse('restore_trash',
                                       kwargs={'account': 'other_account',
                                               'trashname': 't'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('containerview'))

        resp = self.client.get(reverse('restore_trash_collection',
                                          kwargs={'account': 'other_account',
                                               'trashname': 't'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('containerview'))

    def test_trashview(self):
        swiftclient.client.get_auth = mock.Mock(return_value=('/account',
                                                              'a'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_auth = mock.Mock(return_value=('t', 't'))
        swiftclient.client.put_container = mock.Mock()
        swiftclient.client.head_container = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        objects = [{'name': 'obj1', 'last_modified': 0},
                   {'name': 'obj2', 'last_modified': 1}]
        swiftclient.client.head_container = mock.Mock()
        swiftclient.client.get_container = mock.Mock(
                                                    return_value=([], objects))
        swiftclient.client.head_object = mock.Mock(return_value={})
        resp = self.client.get(reverse('trashview',
                                       kwargs={'account': 'account'}))
        objects[0]['size'] = objects[1]['size'] = 0
        objects[0]['dir'] = objects[1]['dir'] = False
        self.assertEqual(resp.context['objects'], objects)

    def test_delete_trash(self):
        swiftclient.client.get_auth = mock.Mock(return_value=('/account',
                                                              'a'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_auth = mock.Mock(return_value=('ts', 'ta'))
        swiftclient.client.delete_object = mock.Mock()
        self.client.get(reverse('delete_trash', kwargs={'account': 'account',
                                                         'trashname': 't'}))
        swiftclient.client.delete_object.assert_called_with('ts', 'ta',
                                                            'account', 't')

    @mock.patch.object(zipfile.ZipFile, '__init__', mock.Mock(
                                                            return_value=None))
    @mock.patch.object(zipfile.ZipFile, 'read', mock.Mock(return_value='c'))
    def test_restore_trash(self):
        url = reverse('restore_trash', kwargs={'account': 'account',
                                               'trashname': 't'})
        swiftclient.client.get_auth = mock.Mock(return_value=('/account',
                                                              'auth'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_auth = mock.Mock(return_value=('ts', 'ta'))
        swiftclient.client.get_object = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url)
        swiftclient.client.get_object.assert_called_with('ts', 'ta',
                                                            'account', 't')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.get_object = mock.Mock(return_value=('a', 'a'))
        swiftclient.client.put_object = mock.Mock(
                          side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url)
        swiftclient.client.put_object.assert_called_with('/account', 'auth',
                                                            't', '', 'c')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.put_object = mock.Mock()

        swiftclient.client.delete_object = mock.Mock()

        resp = self.client.get(url)
        swiftclient.client.delete_object.assert_called_with('ts', 'ta',
                                                            'account', 't')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

    @mock.patch.object(zipfile.ZipFile, '__init__', mock.Mock(
                                                            return_value=None))
    @mock.patch.object(zipfile.ZipFile, 'namelist', mock.Mock(return_value=[]))
    def test_restore_trash_collection(self):
        url = reverse('restore_trash_collection',
                                       kwargs={'account': 'account',
                                               'trashname': 't'})
        swiftclient.client.get_auth = mock.Mock(return_value=('/account',
                                                              'auth'))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_auth = mock.Mock(return_value=('ts', 'ta'))
        swiftclient.client.get_object = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url)
        swiftclient.client.get_object.assert_called_with('ts', 'ta',
                                                            'account', 't')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.get_object = mock.Mock(return_value=('a', 'a'))
        swiftclient.client.head_container = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        swiftclient.client.put_container = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url)
        swiftclient.client.head_container.assert_called_with('/account',
                                                             'auth',
                                                            't')
        swiftclient.client.put_container.assert_called_with('/account',
                                                             'auth',
                                                            't')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.put_container = mock.Mock()

        swiftclient.client.delete_object = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url)
        swiftclient.client.delete_object.assert_called_with('ts', 'ta',
                             'account', 't')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.delete_object = mock.Mock()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.head_container = mock.Mock()
        swiftclient.client.delete_object = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

        swiftclient.client.delete_object = mock.Mock()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('trashview',
                                            kwargs={'account': 'account'}))

    @mock.patch('zipfile.ZipFile', mock.Mock())
    def test_move_to_trash(self):
        container = 'container'
        objectname = 'obj'
        storage_url = '/account'
        auth_token = 'auth'
        orig_container = 'orig_container'
        orig_account = 'orig_account'
        ts_storage_url = 'ts'
        ts_auth_token = 'ta'
        url = reverse('move_to_trash',
                                       kwargs={'container': container,
                                               'objectname': objectname})

        def redirect_resp_check(resp):
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp['Location'],
                             'http://testserver' + reverse('objectview',
                                                kwargs={'container': container,
                                                        'prefix': ''}))

        swiftclient.client.get_auth = mock.Mock(return_value=(storage_url,
                                                              auth_token))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        with mock.patch('swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(None, None))):
            resp = self.client.get(url)
            redirect_resp_check(resp)

        with mock.patch('swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(orig_account,
                                                orig_container))):
            trashname = "%s/%s" % (orig_container, objectname)
            swiftclient.client.get_auth = mock.Mock(return_value=(
                                                                ts_storage_url,
                                                                ts_auth_token))
            swiftclient.client.get_object = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url)
            swiftclient.client.get_object.assert_called_with(storage_url,
                                                             auth_token,
                                                             container,
                                                             objectname)
            redirect_resp_check(resp)

            meta = {'content-length': 0}
            swiftclient.client.get_object = mock.Mock(return_value=(meta,
                                                                    None))
            swiftclient.client.head_container = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            swiftclient.client.put_container = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url)
            swiftclient.client.head_container.assert_called_with(
                                                                ts_storage_url,
                                                                 ts_auth_token,
                                                                orig_account)
            swiftclient.client.put_container.assert_called_with(ts_storage_url,
                                                                 ts_auth_token,
                                                                orig_account)
            redirect_resp_check(resp)

            swiftclient.client.put_container = mock.Mock()
            swiftclient.client.put_object = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url)
            headers = {'X-Delete-After': settings.TRASH_DURABILITY,
                   'x-object-meta-original-length': 0}
            swiftclient.client.put_object.assert_called_with(ts_storage_url,
                                                            ts_auth_token,
                                                            orig_account,
                                                            trashname,
                                                            contents='',
                                                            headers=headers)
            redirect_resp_check(resp)

            swiftclient.client.put_object = mock.Mock()
            swiftclient.client.delete_object = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url)
            expected = [mock.call(storage_url, auth_token, container,
                                  objectname),
                    mock.call(ts_storage_url, ts_auth_token,
                                 orig_account, trashname)]
            self.assertEqual(swiftclient.client.delete_object.call_args_list,
                             expected)
            redirect_resp_check(resp)

            swiftclient.client.delete_object = mock.Mock()
            resp = self.client.get(url)
            redirect_resp_check(resp)

    @mock.patch('zipfile.ZipFile', mock.Mock())
    def test_move_collection_to_trash(self):
        container = 'container'
        storage_url = '/account'
        auth_token = 'auth'
        orig_container = 'orig_container'
        orig_account = 'orig_account'
        ts_storage_url = 'ts'
        ts_auth_token = 'ta'

        def trashname(prefix=''):
            return  "%s/%s" % (orig_container, prefix)

        def url(prefix=''):
            return reverse('move_collection_to_trash',
                                       kwargs={'container': container,
                                               'prefix': prefix})

        def redirect_resp_check(resp, prefix=None):
            self.assertEqual(resp.status_code, 302)
            if prefix:
                self.assertEqual(resp['Location'],
                             'http://testserver' + reverse('objectview',
                                                kwargs={'container': container,
                                                        'prefix': ''}))
            else:
                self.assertEqual(resp['Location'],
                             'http://testserver' + reverse('containerview'))

        swiftclient.client.get_auth = mock.Mock(return_value=(storage_url,
                                                                  auth_token))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        with mock.patch('swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(None, None))):
            resp = self.client.get(url())
            redirect_resp_check(resp)

        with mock.patch('swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(orig_account,
                                                orig_container))):

            swiftclient.client.get_auth = mock.Mock(return_value=(
                                                                ts_storage_url,
                                                                ts_auth_token))
            swiftclient.client.get_container = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            swiftclient.client.get_container.assert_called_with(storage_url,
                                                             auth_token,
                                                             container,
                                                             prefix=None)
            redirect_resp_check(resp)
            resp = self.client.get(url('prefix'))
            swiftclient.client.get_container.assert_called_with(storage_url,
                                                             auth_token,
                                                             container,
                                                             prefix='prefix')
            redirect_resp_check(resp, 'prefix')

            objects = [{'name': 'obj1'}, {'name': 'obj2'}, {'name': 'obj3'}]
            swiftclient.client.get_container = mock.Mock(return_value=(None,
                                                                      objects))

        with mock.patch('swiftbrowser.views.pseudofolder_object_list',
                        mock.Mock(return_value=(None, objects))), mock.patch(
                        'swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(orig_account,
                                                orig_container))):
            swiftclient.client.get_object = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            swiftclient.client.get_object.assert_called_with(storage_url,
                                                             auth_token,
                                                             container,
                                                            objects[0]['name'])
            redirect_resp_check(resp)
            resp = self.client.get(url('prefix'))
            redirect_resp_check(resp, 'prefix')

            meta = {'content-length': 0}
            swiftclient.client.get_object = mock.Mock(return_value=(meta,
                                                                     None))
            swiftclient.client.head_container = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            swiftclient.client.put_container = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            expected = [mock.call(storage_url, auth_token, container,
                                  objects[0]['name']),
                        mock.call(storage_url, auth_token, container,
                                  objects[1]['name']),
                        mock.call(storage_url, auth_token, container,
                                  objects[2]['name'])]
            self.assertEqual(swiftclient.client.get_object.call_args_list,
                              expected)
            swiftclient.client.head_container.assert_called_with(
                                                                ts_storage_url,
                                                                 ts_auth_token,
                                                                orig_account)
            swiftclient.client.put_container.assert_called_with(ts_storage_url,
                                                                 ts_auth_token,
                                                                orig_account)
            redirect_resp_check(resp)
            resp = self.client.get(url('prefix'))
            redirect_resp_check(resp, 'prefix')

            swiftclient.client.put_container = mock.Mock()
            swiftclient.client.put_object = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            headers = {'X-Delete-After': settings.TRASH_DURABILITY,
                   'x-object-meta-original-length': '0'}
            swiftclient.client.put_object.assert_called_with(ts_storage_url,
                                                            ts_auth_token,
                                                            orig_account,
                                                            trashname(), '',
                                        content_type='application/directory',
                                                            headers=headers)
            redirect_resp_check(resp)
            resp = self.client.get(url('prefix'))
            swiftclient.client.put_object.assert_called_with(ts_storage_url,
                                                            ts_auth_token,
                                                            orig_account,
                                                        trashname('prefix'),
                                                        '',
                                        content_type='application/directory',
                                                            headers=headers)
            redirect_resp_check(resp, 'prefix')

            swiftclient.client.put_object = mock.Mock()
            swiftclient.client.delete_object = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            expected = [mock.call(storage_url, auth_token, container,
                                  objects[0]['name']),
                    mock.call(ts_storage_url, ts_auth_token,
                                 orig_account, trashname())]
            self.assertEqual(swiftclient.client.delete_object.call_args_list,
                             expected)
            redirect_resp_check(resp)
            resp = self.client.get(url('prefix'))
            self.assertEqual(
                            swiftclient.client.delete_object.call_args_list[3],
                            mock.call(ts_storage_url, ts_auth_token,
                                 orig_account, trashname('prefix')))
            redirect_resp_check(resp, 'prefix')

            swiftclient.client.delete_object = mock.Mock()
            swiftclient.client.delete_container = mock.Mock(
                            side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            expected = [mock.call(storage_url, auth_token, container,
                                  objects[0]['name']),
                        mock.call(storage_url, auth_token, container,
                                  objects[1]['name']),
                        mock.call(storage_url, auth_token, container,
                                  objects[2]['name']),
                        mock.call(ts_storage_url, ts_auth_token,
                                 orig_account, trashname())]
            self.assertEqual(swiftclient.client.delete_object.call_args_list,
                             expected)
            swiftclient.client.delete_container.assert_called_with(
                                                                storage_url,
                                                                 auth_token,
                                                                container)
            redirect_resp_check(resp)

            swiftclient.client.delete_container = mock.Mock()
            resp = self.client.get(url())
            redirect_resp_check(resp)
            swiftclient.client.delete_container = mock.Mock()
            resp = self.client.get(url('prefix'))
            self.assertFalse(swiftclient.client.delete_container.called)
            redirect_resp_check(resp, 'prefix')

    def test_serve_thumbnail(self):
        container = 'container'
        objectname = 'obj'
        storage_url = '/account'
        auth_token = 'auth'
        orig_container = 'orig_container'
        orig_account = 'orig_account'
        th_storage_url = 'ts'
        th_auth_token = 'ta'
        th_name = "%s_%s" % (orig_container, objectname)

        url = reverse('serve_thumbnail',
                                       kwargs={'container': container,
                                               'objectname': objectname})

        swiftclient.client.get_auth = mock.Mock(return_value=(storage_url,
                                                                  auth_token))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        with mock.patch('swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(None, None))):
            swiftclient.client.head_object = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url)
            swiftclient.client.head_object.assert_called_with(storage_url,
                                                              auth_token,
                                                             container,
                                                             objectname)
            self.assertEqual(resp.status_code, 500)

            swiftclient.client.head_object = mock.Mock()
            self.assertEqual(resp.status_code, 500)

        with mock.patch('swiftbrowser.views.get_original_account',
                        mock.Mock(return_value=(orig_account,
                                                orig_container))), mock.patch(
                        'swiftbrowser.views.create_thumbnail',
                        mock.Mock()) as ct_mock:
            swiftclient.client.get_auth = mock.Mock(return_value=(
                                                                th_storage_url,
                                                                th_auth_token))

            def effect(a, b, c, d):
                if a == th_storage_url:
                    raise swiftclient.client.ClientException('')
                else:
                    return {'x-timestamp': '0'}
            m = mock.Mock()
            m.side_effect = effect
            swiftclient.client.head_object = m
            headers = {'content-type': 'image'}
            swiftclient.client.get_object = mock.Mock(
                        side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url)
            expected = [mock.call(storage_url, auth_token, container,
                                  objectname),
                        mock.call(th_storage_url, th_auth_token, orig_account,
                                  th_name)]
            self.assertEqual(swiftclient.client.head_object.call_args_list,
                             expected)
            self.assert_(ct_mock.called)
            swiftclient.client.get_object.assert_called_with(th_storage_url,
                                                             th_auth_token,
                                                             orig_account,
                                                             th_name)
            self.assertEqual(resp.status_code, 500)

            swiftclient.client.get_object = mock.Mock(return_value=(headers,
                                                                    'x'))
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200)

            ct_mock.reset_mock()

            def effect_2(a, b, c, d):
                if a == th_storage_url:
                    return {'x-timestamp': '1'}
                else:
                    return {'x-timestamp': '0'}
            m = mock.Mock()
            m.side_effect = effect_2
            swiftclient.client.head_object = m
            resp = self.client.get(url)
            self.assertFalse(ct_mock.called)
            self.assertEqual(resp.status_code, 200)

            def effect_3(a, b, c, d):
                    return {'x-timestamp': '0'}
            m = mock.Mock()
            m.side_effect = effect_3
            swiftclient.client.head_object = m
            resp = self.client.get(url)
            self.assertFalse(ct_mock.called)
            self.assertEqual(resp.status_code, 200)

            def effect_4(a, b, c, d):
                if a == th_storage_url:
                    return {'x-timestamp': '0'}
                else:
                    return {'x-timestamp': '1'}
            m = mock.Mock()
            m.side_effect = effect_4
            swiftclient.client.head_object = m
            resp = self.client.get(url)
            self.assert_(ct_mock.called)
            self.assertEqual(resp.status_code, 200)

    @mock.patch('swiftbrowser.utils.Image', mock.Mock())
    @mock.patch('swiftbrowser.views.get_original_account',
                                        mock.Mock(return_value=('orig_account',
                                                'orig_container')))
    def test_create_thumbnail(self):
        container = 'container'
        objectname = 'obj'
        storage_url = '/account'
        auth_token = 'auth'
        orig_container = 'orig_container'
        orig_account = 'orig_account'
        th_storage_url = 'ts'
        th_auth_token = 'ta'
        th_name = "%s_%s" % (orig_container, objectname)

        url = reverse('serve_thumbnail',
                                       kwargs={'container': container,
                                               'objectname': objectname})

        swiftclient.client.get_auth = mock.Mock(return_value=(storage_url,
                                                                  auth_token))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_auth = mock.Mock(return_value=(th_storage_url,
                                                                th_auth_token))

        def effect(a, b, c, d):
            if a == th_storage_url:
                raise swiftclient.client.ClientException('')
            else:
                return {'x-timestamp': '0'}
        m = mock.Mock()
        m.side_effect = effect
        swiftclient.client.head_object = m
        headers = {'content-type': 'image'}
        swiftclient.client.get_object = mock.Mock(return_value=(headers,
                                                                'x'))

        swiftclient.client.head_container = mock.Mock(
                      side_effect=swiftclient.client.ClientException(''))
        swiftclient.client.put_container = mock.Mock(
                      side_effect=swiftclient.client.ClientException(''))
        self.client.get(url)
        swiftclient.client.head_container.assert_called_with(
                            th_storage_url, th_auth_token, orig_account)
        swiftclient.client.put_container.assert_called_with(
                            th_storage_url, th_auth_token, orig_account)

        swiftclient.client.put_container = mock.Mock()
        swiftclient.client.get_object = mock.Mock(
                      side_effect=swiftclient.client.ClientException(''))
        self.client.get(url)
        self.assertEqual(swiftclient.client.get_object.call_args_list[-2],
                    mock.call(storage_url, auth_token, container,
                                   objectname))

        headers = {'content-type': 'image'}
        swiftclient.client.get_object = mock.Mock(return_value=(headers,
                                                                'x'))
        swiftclient.client.put_object = mock.Mock(
                      side_effect=swiftclient.client.ClientException(''))
        self.client.get(url)
        headers = {'X-Delete-After': settings.THUMBNAIL_DURABILITY}
        swiftclient.client.put_object.assert_called_with(th_storage_url,
                                                        th_auth_token,
                                              orig_account, th_name, '',
                                              headers=headers)

    @mock.patch('zipfile.ZipFile', mock.Mock())
    def test_download_collection(self):
        container = 'container'
        storage_url = '/account'
        auth_token = 'auth'
        prefix = 'prefix/'

        def url(prefix=None, non_rec=False):
            kwargs = {'container': container}
            if prefix:
                kwargs['prefix'] = prefix
            if non_rec:
                return reverse('download_collection_nonrec', kwargs=kwargs)
            else:
                return reverse('download_collection', kwargs=kwargs)

        swiftclient.client.get_auth = mock.Mock(return_value=(storage_url,
                                                                  auth_token))
        self.client.post(reverse('login'), {'username': 'test:tester',
                                            'password': 'secret'})

        swiftclient.client.get_container = mock.Mock(
                      side_effect=swiftclient.client.ClientException(''))
        resp = self.client.get(url())
        self.assertEqual(resp.status_code, 403)
        swiftclient.client.get_container.assert_called_with(storage_url,
                                                            auth_token,
                                                            container,
                                                            prefix=None,
                                                            delimiter=None
                                                            )

        resp = self.client.get(url(prefix))
        self.assertEqual(resp.status_code, 403)
        swiftclient.client.get_container.assert_called_with(storage_url,
                                                            auth_token,
                                                            container,
                                                            prefix=prefix,
                                                            delimiter=None
                                                            )

        resp = self.client.get(url(prefix, True))
        self.assertEqual(resp.status_code, 403)
        swiftclient.client.get_container.assert_called_with(storage_url,
                                                            auth_token,
                                                            container,
                                                            prefix=prefix,
                                                            delimiter='/'
                                                            )

        resp = self.client.get(url(non_rec=True))
        self.assertEqual(resp.status_code, 403)
        swiftclient.client.get_container.assert_called_with(storage_url,
                                                            auth_token,
                                                            container,
                                                            prefix=None,
                                                            delimiter='/'
                                                            )

        objs = [{'name': 'obj1'}, {'name': 'obj2'}, {'name': 'obj3'}]
        swiftclient.client.get_container = mock.Mock(return_value=(None, objs))
        m = mock.Mock(side_effect=(lambda o, p: (None, o)))
        with mock.patch('swiftbrowser.views.pseudofolder_object_list', m):
            swiftclient.client.get_object = mock.Mock(
                      side_effect=swiftclient.client.ClientException(''))
            resp = self.client.get(url())
            self.assertEqual(resp.status_code, 403)

            swiftclient.client.get_object = mock.Mock(return_value=(None, ''))
            resp = self.client.get(url())
            expected = [mock.call(storage_url, auth_token, container,
                                           objs[0]['name']),
                        mock.call(storage_url, auth_token, container,
                                           objs[1]['name']),
                        mock.call(storage_url, auth_token, container,
                                           objs[2]['name'])]
            self.assertEqual(swiftclient.client.get_object.call_args_list,
                             expected)
            self.assertEqual(resp['Content-Disposition'], 'attachment; '
                             'filename="%s.zip"' % container)
            self.assertEqual(resp.status_code, 200)

            resp = self.client.get(url(prefix))
            self.assertEqual(resp['Content-Disposition'], 'attachment; '
                             'filename="%s.zip"' % prefix[:-1])
            self.assertEqual(resp.status_code, 200)
