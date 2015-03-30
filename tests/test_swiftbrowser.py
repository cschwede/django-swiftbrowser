#!/usr/bin/python
# -*- coding: utf8 -*-

import mock
import random

from django.test import TestCase
from django.core.urlresolvers import reverse

import swiftclient
import swiftbrowser


class MockTest(TestCase):
    """ Unit tests for swiftbrowser

    All calls using python-swiftclient.clients are replaced using mock """

    def test_container_view(self):
        swiftclient.client.get_account = mock.Mock(
            return_value=[{}, []],
            side_effect=swiftclient.client.ClientException(''))

        resp = self.client.get(reverse('containerview'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'],
                         'http://testserver' + reverse('login'))

        swiftclient.client.get_account = mock.Mock(
            return_value=[{}, []],
            side_effect=swiftclient.client.ClientException(
                '', http_status=403))
        resp = self.client.get(reverse('containerview'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue("Container listing failed" in resp.content)

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

        swiftclient.client.delete_container = mock.Mock()
        resp = self.client.post(reverse('delete_container',
                                kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

        expected = [mock.call('', '', 'container', 'obj1'),
                    mock.call('', '', 'container', 'obj2')]
        swiftclient.client.delete_object.call_args_list == expected

        swiftclient.client.delete_container = mock.Mock()

        resp = self.client.post(reverse('delete_container',
                                kwargs={'container': 'container'}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'http://testserver/')

    def test_objectview(self):
        swiftclient.client.get_container = mock.Mock(
            return_value=[{}, []],
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
        swiftbrowser.utils.get_temp_url = mock.Mock(return_value="http://url")

        resp = self.client.get(reverse('download', kwargs={
                                       'container': 'container',
                                       'objectname': 'testfile'}))
        self.assertEqual(resp['Location'], "http://url")

        swiftbrowser.utils.get_temp_url = mock.Mock(return_value=None)
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

        swiftclient.client.post_container.assert_called_with(
            '', '', 'container', {'X-Container-Read': '.r:*,.rlistings'})

        swiftclient.client.head_container = mock.Mock(return_value={
            'x-container-read': 'x,.r:*,.rlistings'})
        response = self.client.get(reverse('toggle_public',
                                           kwargs={'container': 'container'}))
        self.assertEqual(response.status_code, 302)

        swiftclient.client.post_container.assert_called_with(
            '', '', 'container', {'X-Container-Read': 'x,'})

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
        swiftclient.client.post_account.assert_called_with(
            'dummy', 'dummy', {'x-account-meta-temp-url-key': 'a' * 32})

        # Authorized, temp url key already set
        account = [{'x-account-meta-temp-url-key': 'dummy'}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))
        self.assertIsNotNone(swiftbrowser.utils.get_temp_key("dummy", "dummy"))

    def test_tempurl(self):
        swiftclient.client.get_account = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))
        response = self.client.get(reverse('tempurl', args=['c', 'o']))
        self.assertEqual(response.status_code, 302)

        account = [{'x-account-meta-temp-url-key': 'dummy'}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))

        response = self.client.get(reverse('tempurl', args=['c', 'o']))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('tempurl', args=['ü', 'ö']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['container'], u'ü')
        self.assertEqual(response.context['objectname'], u'ö')

    def test_create_pseudofolder(self):
        swiftclient.client.put_object = mock.Mock(
            side_effect=swiftclient.client.ClientException(''))

        swiftclient.client.put_container('storage_url',
                                         'auth_token',
                                         'container')

        resp = self.client.post(reverse(
            'create_pseudofolder',
            kwargs={'container': 'container'}),
            {'foldername': 'test'})
        self.assertEqual(resp.status_code, 302)

        swiftclient.client.put_object.assert_called_with(
            '', '', u'container', u'test/',
            None, content_type='application/directory')

        resp = self.client.post(reverse(
            'create_pseudofolder',
            kwargs={'container': 'container', 'prefix': 'prefix'}),
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
        swiftclient.client.post_container.assert_called_with(
            '', '', 'container',
            {'X-Container-Read': ',testuser',
             'X-Container-Write': ',testuser'})
