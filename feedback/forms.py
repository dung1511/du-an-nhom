from django import forms
from rooms.models import Room

from .models import Feedback

class FeedbackForm(forms.ModelForm):
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Enter your name', 'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Enter your email', 'class': 'form-control'}))

    class Meta:
        model = Feedback
        fields = ['name', 'email', 'country', 'rating', 'comment']
        widgets = {
            'country': forms.TextInput(attrs={'placeholder': 'Enter your country', 'class': 'form-control'}),
            'rating': forms.RadioSelect(choices=[(i, f'⭐ {i}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your feedback...', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(FeedbackForm, self).__init__(*args, **kwargs)
        if self.user and self.user.is_authenticated:
            # For authenticated users, set name and email as read-only with profile values
            self.fields['name'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['name'].initial = self.user.get_full_name()
            self.fields['email'].initial = self.user.email
        else:
            # For non-authenticated users, make all fields editable and required
            self.fields['name'].required = True
            self.fields['email'].required = True


class FeedbackListForm(FeedbackForm):
    room = forms.ModelChoiceField(
        queryset=Room.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Chọn phòng để đánh giá',
    )

    class Meta:
        model = Feedback
        fields = ['room', 'name', 'email', 'country', 'rating', 'comment']
        widgets = {
            'country': forms.TextInput(attrs={'placeholder': 'Quê quán / quốc gia', 'class': 'form-control'}),
            'rating': forms.RadioSelect(choices=[(i, f'⭐ {i}') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Chia sẻ trải nghiệm của bạn...', 'class': 'form-control'}),
        }