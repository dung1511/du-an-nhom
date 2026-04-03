from django import forms
from .models import Contact

class ContactForm(forms.ModelForm):
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Name', 'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'}))

    class Meta:
        model = Contact
        fields = ['name', 'email', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Message', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        # Make all fields editable and required for everyone
        self.fields['name'].required = True
        self.fields['email'].required = True