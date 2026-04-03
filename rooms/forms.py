from django import forms
from .models import Reservation
from datetime import date

class BookingForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            'check_in_date', 'check_out_date', 'adults', 'children',
            'first_name', 'last_name', 'email', 'phone', 'address',
            'city', 'state', 'postcode', 'adhar_id', 'note'
        ]
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Required fields
        self.fields['check_in_date'].required = True
        self.fields['check_out_date'].required = True
        self.fields['adults'].required = True
        self.fields['children'].required = False

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

    def clean(self):
        cleaned_data = super().clean()

        check_in = cleaned_data.get('check_in_date')
        check_out = cleaned_data.get('check_out_date')
        adults = cleaned_data.get('adults')
        children = cleaned_data.get('children') or 0

        # Check date
        if check_in and check_out:
            if check_in < date.today():
                raise forms.ValidationError("Ngày nhận phòng không được nhỏ hơn hôm nay.")
            if check_out <= check_in:
                raise forms.ValidationError("Ngày trả phòng phải sau ngày nhận phòng.")

        # Check guests
        if adults is not None and adults <= 0:
            raise forms.ValidationError("Số người lớn phải lớn hơn 0.")

        if children < 0:
            raise forms.ValidationError("Số trẻ em không hợp lệ.")

        return cleaned_data