# Import thư viện forms của Django
from django import forms

# Import model Reservation và Service từ models.py
from .models import Reservation, Service


# Tạo form BookingForm kế thừa từ ModelForm
# ModelForm giúp tạo form tự động từ model
class BookingForm(forms.ModelForm):

    # Class Meta dùng để cấu hình form
    class Meta:

        # Chỉ định model liên kết với form
        model = Reservation

        # Các field sẽ hiển thị trong form
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'note'
        ]

        # Tùy chỉnh giao diện các input
        widgets = {

            # Ô nhập first_name
            'first_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your first name'
                }
            ),

            # Ô nhập last_name
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

            # Ô nhập ghi chú
            'note': forms.Textarea(
                attrs={
                    'rows': 5,
                    'placeholder':
                    'Add any special requests or notes for your booking...'
                }
            ),
        }

    # Hàm khởi tạo form
    def __init__(self, *args, **kwargs):

        # Gọi constructor của class cha
        super().__init__(*args, **kwargs)

        # ===== REQUIRED FIELDS =====

        # Bắt buộc nhập first_name
        self.fields['first_name'].required = True

        # Bắt buộc nhập last_name
        self.fields['last_name'].required = True

        # Bắt buộc nhập email
        self.fields['email'].required = True

        # Bắt buộc nhập phone
        self.fields['phone'].required = True

        # Bắt buộc nhập address
        self.fields['address'].required = True

        # Bắt buộc nhập city
        self.fields['city'].required = True

        # note không bắt buộc
        self.fields['note'].required = False


        # ===== SET LABELS =====

        # Đặt label cho first_name
        self.fields['first_name'].label = 'First Name'

        # Đặt label cho last_name
        self.fields['last_name'].label = 'Last Name'

        # Đặt label cho email
        self.fields['email'].label = 'Email Address'

        # Đặt label cho phone
        self.fields['phone'].label = 'Phone Number'

        # Đặt label cho address
        self.fields['address'].label = 'Street Address'

        # Đặt label cho city
        self.fields['city'].label = 'City'

        # Đặt label cho note
        self.fields['note'].label = 'Special Requests'


    # Hàm validate toàn bộ form
    def clean(self):

        # Lấy dữ liệu đã được validate
        cleaned_data = super().clean()

        # Có thể thêm validate custom tại đây
        # Ví dụ:
        # - Kiểm tra số điện thoại
        # - Kiểm tra email
        # - Kiểm tra độ dài dữ liệu

        # Trả dữ liệu đã xử lý
        return cleaned_data



# Form chọn dịch vụ đi kèm
class ServiceSelectionForm(forms.Form):

    # Tạo field chọn nhiều dịch vụ
    services = forms.ModelMultipleChoiceField(

        # Lấy tất cả dịch vụ đang active
        queryset=Service.objects.filter(
            active=True
        ).order_by(
            'order',
            'name'
        ),

        # Không bắt buộc chọn
        required=False,

        # Hiển thị dạng checkbox
        widget=forms.CheckboxSelectMultiple,

        # Label hiển thị trên form
        label='Dịch vụ đi kèm',
    )