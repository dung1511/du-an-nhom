from django import forms
from .models import Blog, Comment

class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ['title', 'description', 'country', 'category', 'image1', 'image2']

class CommentForm(forms.ModelForm):
    name = forms.CharField(required=False)

    class Meta:
        model = Comment
        fields = ['name', 'comment']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(CommentForm, self).__init__(*args, **kwargs)
        if self.user and self.user.is_authenticated:
            self.fields['name'].widget = forms.HiddenInput()
        else:
            self.fields['name'].required = True