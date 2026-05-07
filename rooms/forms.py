from django import forms
from .models import Reservation, Service


# =========================
# FORM ĐẶT PHÒNG
# =========================
class BookingForm(forms.ModelForm):

    class Meta:
        # Form này liên kết với model Reservation
        model = Reservation

        # Các field sẽ hiển thị trên form
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'note'
        ]

        # Tùy chỉnh giao diện input
        widgets = {

            # Ô nhập tên
            'first_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your first name'
                }
            ),

            # Ô nhập họ
            'last_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your last name'
                }
            ),

            # Ô nhập email
            'email': forms.EmailInput(
                attrs={
                    'placeholder': 'your.email@example.com'
                }
            ),

            # Ô nhập số điện thoại
            'phone': forms.TextInput(
                attrs={
                    'placeholder': '+91 98765 43210'
                }
            ),

            # Ô nhập địa chỉ
            'address': forms.TextInput(
                attrs={
                    'placeholder': 'Street address'
                }
            ),

            # Ô nhập thành phố
            'city': forms.TextInput(
                attrs={
                    'placeholder': 'City'
                }
            ),

            # Ô ghi chú
            'note': forms.Textarea(
                attrs={
                    'rows': 5,
                    'placeholder': 'Add any special requests or notes for your booking...'
                }
            ),
        }

    # Hàm khởi tạo form
    def __init__(self, *args, **kwargs):

        # Gọi constructor của class cha
        super().__init__(*args, **kwargs)

        # =========================
        # REQUIRED FIELDS
        # =========================

        # Bắt buộc nhập
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['address'].required = True
        self.fields['city'].required = True

        # Không bắt buộc nhập
        self.fields['note'].required = False

        # =========================
        # LABEL HIỂN THỊ
        # =========================

        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email Address'
        self.fields['phone'].label = 'Phone Number'
        self.fields['address'].label = 'Street Address'
        self.fields['city'].label = 'City'
        self.fields['note'].label = 'Special Requests'

    # =========================
    # VALIDATE TOÀN BỘ FORM
    # =========================
    def clean(self):

        # Lấy dữ liệu sau khi Django xử lý
        cleaned_data = super().clean()

        # Có thể kiểm tra dữ liệu tại đây
        # Ví dụ:
        # if cleaned_data['city'] == 'abc':
        #     raise forms.ValidationError("City không hợp lệ")

        return cleaned_data


# =========================
# FORM CHỌN DỊCH VỤ
# =========================
class ServiceSelectionForm(forms.Form):

    # Field chọn nhiều dịch vụ
    services = forms.ModelMultipleChoiceField(

        # Lấy các dịch vụ active=True
        queryset=Service.objects.filter(
            active=True
        ).order_by('order', 'name'),

        # Không bắt buộc chọn
        required=False,

        # Hiển thị dạng checkbox
        widget=forms.CheckboxSelectMultiple,

        # Label hiển thị ngoài giao diện
        label='Dịch vụ đi kèm',
    )