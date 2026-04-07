from django import forms
from .models import Reservation, Service

class BookingForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'address',
            'city', 'note'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter your first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter your last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'your.email@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91 98765 43210'}),
            'address': forms.TextInput(attrs={'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'note': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Add any special requests or notes for your booking...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Required fields
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['address'].required = True
        self.fields['city'].required = True
        self.fields['note'].required = False

        # Set labels
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email Address'
        self.fields['phone'].label = 'Phone Number'
        self.fields['address'].label = 'Street Address'
        self.fields['city'].label = 'City'
        self.fields['note'].label = 'Special Requests'

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class ServiceSelectionForm(forms.Form):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(active=True).order_by('order', 'name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Dịch vụ đi kèm',
    )