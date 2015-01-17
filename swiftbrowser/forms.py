""" Forms for swiftbrowser.browser """
# -*- coding: utf-8 -*-
from django import forms


class CreateContainerForm(forms.Form):
    """ Simple form for container creation """
    containername = forms.CharField(max_length=100)


class AddACLForm(forms.Form):
    """ Form for ACLs """
    username = forms.CharField(max_length=100)
    read = forms.BooleanField(required=False)
    write = forms.BooleanField(required=False)


class PseudoFolderForm(forms.Form):
    """ Upload form """
    foldername = forms.CharField(max_length=100)


class LoginForm(forms.Form):
    """ Login form """
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
