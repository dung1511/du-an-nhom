from django import forms
from .models import Profile
from django.contrib.auth.models import User

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    username = forms.CharField(required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'username', 'email', 'phone_number', 'profile_picture']

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].initial = self.instance.user.first_name
        self.fields['last_name'].initial = self.instance.user.last_name
        self.fields['username'].initial = self.instance.user.username
        self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super(ProfileForm, self).save(commit=False)
        profile.user.first_name = self.cleaned_data['first_name']
        profile.user.last_name = self.cleaned_data['last_name']
        profile.user.username = self.cleaned_data['username']
        profile.user.email = self.cleaned_data['email']
        if commit:
            profile.user.save()
            profile.save()
        return profile