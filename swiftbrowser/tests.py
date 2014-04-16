#!/usr/bin/python
# -*- coding: utf8 -*-
#pylint:disable=E1103

import mock
import random

from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse

import swiftclient
import swiftbrowser


class MockTest(TestCase):
    """ Unit tests for swiftbrowser

    All calls using python-swiftclient.clients are replaced using mock """

    def test_container_view(self):
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
        self.assertEqual(response.status_code, 302)

        account = [{'x-account-meta-temp-url-key': 'dummy'}, ]
        swiftclient.client.get_account = mock.Mock(return_value=(account))

        response = self.client.get(reverse('tempurl', args=['c', 'o']))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('tempurl', args=['ü', 'ö']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['container'], 'ü')
        self.assertEqual(response.context['objectname'], 'ö')

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
