# Import permissions từ Django REST Framework
from rest_framework import permissions


# Tạo class phân quyền custom
# Kế thừa từ BasePermission
class IsStaffOrAdmin(permissions.BasePermission):


    # Hàm kiểm tra quyền truy cập
    # request -> chứa thông tin request hiện tại
    # view -> view đang được gọi
    def has_permission(self, request, view):


        # bool(...)
        # Ép kết quả về True hoặc False
        return bool(

            # Kiểm tra user có tồn tại không
            request.user

            # Kiểm tra user đã đăng nhập chưa
            and request.user.is_authenticated

            # Kiểm tra:
            # - là staff
            # HOẶC
            # - là superuser/admin
            and (
                request.user.is_staff
                or request.user.is_superuser
            )
        )