from django import forms
from .models import Reservation

class BookingForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'address', 'city',
            'state', 'postcode', 'adhar_id', 'note'  
        ]
        widgets = {
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['address'].required = True
        self.fields['city'].required = True
        self.fields['state'].required = True
        self.fields['postcode'].required = True
        self.fields['adhar_id'].required = True
        self.fields['note'].required = False