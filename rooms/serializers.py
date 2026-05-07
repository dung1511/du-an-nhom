from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User

from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import Coupon, Reservation, Room, RoomCategory, Service


# ===== SERIALIZER DỊCH VỤ =====
class ServiceSerializer(serializers.ModelSerializer):


    # ===== META =====
    class Meta:

        # Model sử dụng
        model = Service

        # Các field sẽ trả về JSON
        fields = [

            "id",              # ID dịch vụ
            "name",            # Tên dịch vụ
            "slug",            # Slug URL
            "description",     # Mô tả
            "price",           # Giá
            "image",           # Ảnh upload
            "image_url",       # URL ảnh
            "active",          # Trạng thái
            "order"            # Thứ tự hiển thị
        ]




# ===== SERIALIZER TẠO BOOKING =====
class ReservationCreateSerializer(serializers.ModelSerializer):


    # ===== ROOM =====

    # Nhận room trực tiếp bằng ID
    room = serializers.PrimaryKeyRelatedField(

        # Query tất cả phòng
        queryset=Room.objects.all(),

        # Chỉ dùng khi ghi dữ liệu
        write_only=True,

        # Không bắt buộc
        required=False
    )


    # room_id -> map sang room
    room_id = serializers.PrimaryKeyRelatedField(

        queryset=Room.objects.all(),

        # source="room"
        # -> gán vào field room
        source="room",

        write_only=True,

        required=False
    )


    # ===== USER =====

    # ID người dùng
    user_id = serializers.IntegerField(

        required=False,

        write_only=True
    )


    # ===== EMAIL =====

    # Email bắt buộc
    email = serializers.EmailField(required=True)


    # ===== COUPON =====

    # Mã giảm giá
    coupon_code = serializers.CharField(

        required=False,

        allow_blank=True,

        write_only=True
    )



    # ===== META =====
    class Meta:

        # Model sử dụng
        model = Reservation


        # Field trả về API
        fields = [

            "id",
            "room_id",
            "user_id",
            "room",
            "check_in_date",
            "check_out_date",
            "adults",
            "children",
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "postcode",
            "adhar_id",
            "note",
            "payment_method",
            "payment_status",
            "coupon_code",
            "subtotal",
            "gst",
            "deposit_percentage",
            "deposit_amount",
            "balance_due",
            "discount_applied",
            "service_total",
            "total",
            "damage_fee",
            "final_total",
            "created_at",
            "checkout_at",
        ]


        # Các field chỉ đọc
        read_only_fields = [

            "id",
            "room",
            "subtotal",
            "gst",
            "deposit_percentage",
            "deposit_amount",
            "balance_due",
            "discount_applied",
            "service_total",
            "total",
            "damage_fee",
            "final_total",
            "payment_status",
            "created_at",
            "checkout_at",
        ]



    # ===== VALIDATE =====
    def validate(self, attrs):


        # ===== LẤY DỮ LIỆU =====
        room = attrs["room"]

        check_in = attrs.get("check_in_date")

        check_out = attrs.get("check_out_date")

        adults = attrs.get("adults", 1)

        children = attrs.get("children", 0)



        # ===== KIỂM TRA NGÀY =====

        # Nếu thiếu ngày
        if not check_in or not check_out:

            raise serializers.ValidationError(
                "Vui long cung cap ngay check-in va check-out."
            )


        # Nếu check-in nhỏ hơn hôm nay
        if check_in < date.today():

            raise serializers.ValidationError(
                "Ngay check-in khong duoc nho hon hom nay."
            )


        # Nếu checkout <= checkin
        if check_out <= check_in:

            raise serializers.ValidationError(
                "Ngay check-out phai sau ngay check-in."
            )



        # ===== KIỂM TRA KHÁCH =====

        # Người lớn <= 0
        if adults <= 0:

            raise serializers.ValidationError(
                "So nguoi lon phai lon hon 0."
            )


        # Trẻ em < 0
        if children < 0:

            raise serializers.ValidationError(
                "So tre em khong hop le."
            )



        # ===== KIỂM TRA SỨC CHỨA =====
        if not room.can_accommodate(
            adults=adults,
            children=children
        ):

            raise serializers.ValidationError(

                (
                    f"Phong chi cho toi da "
                    f"{room.total_capacity} khach "
                    f"({room.capacity_adults} nguoi lon, "
                    f"{room.capacity_children} tre em)."
                )
            )



        # ===== KIỂM TRA PHÒNG TRỐNG =====
        if not room.is_available(check_in, check_out):

            raise serializers.ValidationError(
                "Phong da duoc dat trong khoang thoi gian nay."
            )



        # ===== REQUEST =====
        request = self.context.get("request")

        # User hiện tại
        actor = getattr(request, "user", None)



        # ===== USER ID =====
        user_id = attrs.pop("user_id", None)


        # Nếu có user_id
        if user_id is not None:

            # Chỉ admin/staff mới được gán user khác
            if (

                not actor
                or not actor.is_authenticated
                or not (
                    actor.is_staff
                    or actor.is_superuser
                )
            ):

                raise serializers.ValidationError(
                    "Chi staff/admin moi co the gan booking cho nguoi dung khac."
                )


            try:

                # Gán user
                attrs["user"] = User.objects.get(pk=user_id)

            except User.DoesNotExist as exc:

                raise serializers.ValidationError(
                    "Nguoi dung khong ton tai."
                ) from exc


        # Nếu user đã login
        elif (

            actor
            and actor.is_authenticated
            and not (
                actor.is_staff
                or actor.is_superuser
            )
        ):

            # Gán booking cho user hiện tại
            attrs["user"] = actor



        # ===== COUPON =====
        coupon_code = attrs.pop(
            "coupon_code",
            ""
        ).strip()

        coupon = None


        # Nếu có coupon
        if coupon_code:

            try:

                # Tìm coupon hợp lệ
                coupon = Coupon.objects.get(

                    code=coupon_code,

                    active=True,

                    valid_from__lte=date.today(),

                    valid_to__gte=date.today(),
                )

            except Coupon.DoesNotExist:

                raise serializers.ValidationError(
                    "Ma giam gia khong hop le hoac da het han."
                )


        # Gán coupon
        attrs["coupon"] = coupon

        return attrs



    # ===== CREATE =====
    def create(self, validated_data):


        # ===== LẤY DỮ LIỆU =====
        room = validated_data["room"]

        check_in = validated_data["check_in_date"]

        check_out = validated_data["check_out_date"]

        coupon = validated_data.pop("coupon", None)



        # ===== TÍNH SỐ ĐÊM =====
        num_nights = (

            check_out -
            check_in
        ).days



        # ===== TÍNH TIỀN =====

        # Tiền phòng
        subtotal = room.price * num_nights


        # Thuế GST 18%
        gst = subtotal * Decimal("0.18")


        # Giảm giá
        discount = Decimal("0.00")


        # Nếu có coupon
        if coupon:

            discount = (
                subtotal *
                coupon.discount_percentage
            ) / Decimal("100")


        # Tổng tiền
        total = subtotal + gst - discount



        # ===== GÁN DỮ LIỆU =====
        validated_data["subtotal"] = subtotal

        validated_data["gst"] = gst

        validated_data["discount_applied"] = discount

        validated_data["total"] = total

        validated_data["coupon"] = coupon



        # ===== TẠO BOOKING =====
        reservation = Reservation(
            **validated_data
        )


        # Đồng bộ tiền
        reservation.sync_financial_fields()


        # Lưu database
        reservation.save()


        # Trả booking
        return reservation


# ===== SERIALIZER CHECK-IN =====
class ReservationCheckInSerializer(serializers.Serializer):

    # Mã booking để tìm reservation
    booking_code = serializers.CharField(required=True, write_only=True)
    
    # Số lượng khách lớn check-in
    checked_in_adults = serializers.IntegerField(required=True, write_only=True)
    
    # Số lượng trẻ em check-in (tuỳ chọn)
    checked_in_children = serializers.IntegerField(required=False, write_only=True, default=0)
    
    # Ngày check-in thực tế (tuỳ chọn, cho check-in sớm)
    actual_check_in_date = serializers.DateField(required=False, write_only=True, allow_null=True)

    def validate(self, data):
        # Lấy booking code
        booking_code = data.get('booking_code')
        
        # Tìm reservation theo booking code
        try:
            reservation = Reservation.objects.get(booking_code=booking_code)
        except Reservation.DoesNotExist:
            raise DRFValidationError('Booking code không tồn tại.')
        
        # Sử dụng method can_check_in() để kiểm tra
        can_check_in, message = reservation.can_check_in()
        if not can_check_in:
            raise DRFValidationError(message)
        
        # Kiểm tra số lượng khách
        checked_in_adults = data.get('checked_in_adults', 1)
        if checked_in_adults < 1:
            raise DRFValidationError('Số lượng khách lớn phải >= 1.')
        
        if checked_in_adults > reservation.adults:
            raise DRFValidationError(f'Số khách check-in vượt quá dự đoán ({reservation.adults}).')
        
        # Lưu reservation vào validated_data
        data['reservation'] = reservation
        
        return data


# ===== SERIALIZER CHECKOUT =====
class ReservationCheckoutSerializer(serializers.ModelSerializer):

    """
    Serializer dùng để xử lý trả phòng (checkout)
    """


    # ===== TÊN PHÒNG =====

    # Lấy tên phòng từ:
    # reservation.room.name
    room_name = serializers.CharField(

        source='room.name',

        # Chỉ đọc
        read_only=True
    )


    # ===== NGÀY CHECKOUT =====

    # Lấy dữ liệu từ:
    # check_out_date
    checkout_date = serializers.DateField(

        source='check_out_date',

        read_only=True
    )


    # ===== THỜI GIAN CHECKOUT THỰC TẾ =====

    checkout_at = serializers.DateTimeField(

        read_only=True
    )


    # ===== BÁO CÁO HƯ HỎNG =====

    damage_reported = serializers.BooleanField(

        # Không bắt buộc
        required=False,

        # Mặc định False
        default=False
    )


    # ===== GHI CHÚ HƯ HỎNG =====

    damage_notes = serializers.CharField(

        required=False,

        # Cho phép chuỗi rỗng
        allow_blank=True,

        # Cho phép null
        allow_null=True
    )



    # ===== META =====
    class Meta:

        # Model sử dụng
        model = Reservation


        # Các field trả về API
        fields = [

            'id',                         # ID booking
            'room_name',                  # Tên phòng
            'check_in_date',              # Ngày checkin
            'check_out_date',             # Ngày checkout dự kiến
            'checkout_date',              # Alias checkout
            'is_checked_in',              # Đã checkin chưa
            'checked_in_at',              # Thời gian checkin
            'checked_in_adults',          # Số người lớn checkin
            'checked_in_children',        # Số trẻ em checkin
            'user',                       # User đặt
            'first_name',                 # Tên
            'last_name',                  # Họ
            'email',                      # Email
            'phone',                      # SĐT
            'total',                      # Tổng tiền
            'deposit_amount',             # Tiền cọc
            'balance_due',                # Tiền còn lại
            'damage_reported',            # Có hư hỏng không
            'damage_notes',               # Ghi chú hư hỏng
            'damage_fee',                 # Phí hư hỏng
            'final_total',                # Tổng cuối cùng
            'payment_status',             # Trạng thái thanh toán
            'is_checked_out',             # Đã checkout chưa
            'checkout_at',                # Thời gian checkout
        ]


        # ===== FIELD CHỈ ĐỌC =====
        read_only_fields = [

            'id',
            'room_name',
            'check_in_date',
            'check_out_date',
            'checkout_date',
            'is_checked_in',
            'checked_in_at',
            'checked_in_adults',
            'checked_in_children',
            'user',
            'first_name',
            'last_name',
            'email',
            'phone',
            'total',
            'deposit_amount',
            'balance_due',
            'damage_fee',
            'final_total',
            'payment_status',
            'checkout_at',
        ]



    # ===== UPDATE CHECKOUT =====
    def update(self, instance, validated_data):


        # ===== LẤY DỮ LIỆU HƯ HỎNG =====

        # Có hư hỏng không
        damage_reported = validated_data.pop(

            'damage_reported',

            False
        )


        # Ghi chú hư hỏng
        damage_notes = validated_data.pop(

            'damage_notes',

            ''
        ) or ''



        # ===== CHECKOUT =====

        # Đánh dấu đã checkout
        instance.is_checked_out = True



        # Nếu chưa có thời gian checkout
        if not instance.checkout_at:

            # Lưu thời gian hiện tại
            instance.checkout_at = datetime.now()



        # ===== THÔNG TIN HƯ HỎNG =====

        # True/False
        instance.damage_reported = bool(
            damage_reported
        )


        # Nội dung hư hỏng
        instance.damage_notes = damage_notes



        # ===== TÍNH PHÍ HƯ HỎNG =====

        # Nếu có hư hỏng
        if instance.damage_reported:

            # Tính phí
            instance.damage_fee = (
                instance.calculate_damage_fee()
            )

        else:

            # Không có hư hỏng
            instance.damage_fee = Decimal('0.00')



        # ===== TỔNG TIỀN CUỐI =====

        instance.final_total = (

            instance.total +

            instance.damage_fee
        )



        # ===== LƯU DATABASE =====
        instance.save(

            update_fields=[

                'is_checked_out',

                'checkout_at',

                'damage_reported',

                'damage_notes',

                'damage_fee',

                'final_total',
            ]
        )


        # Trả object đã update
        return instance




# ===== SERIALIZER CHI TIẾT BOOKING =====
class ReservationDetailSerializer(serializers.ModelSerializer):

    """
    Serializer dùng để xem chi tiết đặt phòng
    """


    # ===== TÊN PHÒNG =====
    room_name = serializers.CharField(

        source='room.name',

        read_only=True
    )



    # ===== GIÁ PHÒNG =====
    room_price = serializers.DecimalField(

        # Lấy giá từ room.price
        source='room.price',

        # Tối đa 10 số
        max_digits=10,

        # 2 số thập phân
        decimal_places=2,

        # Chỉ đọc
        read_only=True
    )



    # ===== DANH SÁCH DỊCH VỤ =====

    # many=True
    # -> nhiều service
    selected_services = ServiceSerializer(

        many=True,

        read_only=True
    )



    # ===== FIELD TỰ TÍNH =====

    # SerializerMethodField
    # -> gọi hàm get_num_nights()
    num_nights = serializers.SerializerMethodField()



    # ===== META =====
    class Meta:

        # Model sử dụng
        model = Reservation


        # Các field trả về
        fields = [

            'id',
            'room_name',
            'room_price',
            'check_in_date',
            'check_out_date',
            'is_checked_in',
            'checked_in_at',
            'checked_in_adults',
            'checked_in_children',
            'num_nights',
            'adults',
            'children',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'state',
            'postcode',
            'subtotal',
            'gst',
            'deposit_percentage',
            'deposit_amount',
            'balance_due',
            'discount_applied',
            'service_total',
            'selected_services',
            'total',
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'final_total',
            'payment_method',
            'payment_status',
            'is_checked_out',
            'created_at',
            'checkout_at',
            'deposit_receipt',
            'deposit_receipt_uploaded_at',
            'deposit_confirmed',
            'deposit_confirmed_at',
        ]



    # ===== TÍNH SỐ ĐÊM =====
    def get_num_nights(self, obj):


        # Nếu có ngày checkin/checkout
        if obj.check_in_date and obj.check_out_date:


            # Tính số ngày
            return (

                obj.check_out_date -

                obj.check_in_date

            ).days


        # Không có dữ liệu
        return 0

# ===== SERIALIZER BOOKING ĐÃ TRẢ VỀ API =====
class ReturnedReservationSerializer(serializers.ModelSerializer):


    # ===== ROOM =====

    # SerializerMethodField
    # -> gọi hàm get_room()
    room = serializers.SerializerMethodField()



    # ===== USER =====

    # Gọi hàm get_user()
    user = serializers.SerializerMethodField()



    # ===== COUPON =====

    # Lấy coupon.code
    coupon_code = serializers.CharField(

        source='coupon.code',

        read_only=True
    )



    # ===== SỐ ĐÊM =====

    num_nights = serializers.SerializerMethodField()



    # ===== TỔNG KHÁCH =====

    total_guests = serializers.SerializerMethodField()



    # ===== META =====
    class Meta:

        # Model sử dụng
        model = Reservation


        # Các field trả về
        fields = [

            'id',
            'room',
            'user',
            'coupon_code',
            'check_in_date',
            'check_out_date',
            'is_checked_in',
            'checked_in_at',
            'checked_in_adults',
            'checked_in_children',
            'num_nights',
            'adults',
            'children',
            'total_guests',
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'state',
            'postcode',
            'adhar_id',
            'note',
            'subtotal',
            'gst',
            'deposit_percentage',
            'deposit_amount',
            'balance_due',
            'discount_applied',
            'total',
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'final_total',
            'payment_method',
            'payment_status',
            'is_checked_out',
            'created_at',
            'checkout_at',
        ]



    # ===== LẤY USER =====
    def get_user(self, obj):


        # Nếu không có user
        if not obj.user:

            return None



        # Lấy profile user
        profile = getattr(

            obj.user,

            'profile',

            None
        )



        # Trả dữ liệu user dạng dictionary
        return {

            'id': obj.user.id,

            'username': obj.user.username,

            'first_name': obj.user.first_name,

            'last_name': obj.user.last_name,

            'email': obj.user.email,

            'phone_number': (
                profile.phone_number
                if profile else None
            ),
        }



    # ===== LẤY THÔNG TIN PHÒNG =====
    def get_room(self, obj):


        # Serialize room
        return RoomSerializer(
            obj.room
        ).data



    # ===== TÍNH SỐ ĐÊM =====
    def get_num_nights(self, obj):


        # Nếu có ngày
        if obj.check_in_date and obj.check_out_date:


            # Tính số đêm
            return (

                obj.check_out_date -

                obj.check_in_date

            ).days


        return 0



    # ===== TỔNG KHÁCH =====
    def get_total_guests(self, obj):


        # adults + children
        return (

            (obj.adults or 0)

            +

            (obj.children or 0)
        )






# ===== SERIALIZER ROOM =====
class RoomSerializer(serializers.ModelSerializer):

    """
    Serializer hiển thị thông tin phòng
    """


    # ===== TRẠNG THÁI =====

    availability_status = serializers.SerializerMethodField()



    # ===== PHÒNG CÒN TRỐNG =====

    is_available_now = serializers.SerializerMethodField()



    # ===== TÊN PHÒNG =====

    room_title = serializers.CharField(

        source='name',

        read_only=True
    )



    # ===== SỨC CHỨA NGƯỜI LỚN =====

    max_adult = serializers.IntegerField(

        source='capacity_adults',

        read_only=True
    )



    # ===== SỨC CHỨA TRẺ EM =====

    max_children = serializers.IntegerField(

        source='capacity_children',

        read_only=True
    )



    # ===== META =====
    class Meta:

        model = Room


        fields = [

            'id',
            'name',
            'room_title',
            'category',
            'capacity',
            'size',
            'max_adult',
            'max_children',
            'capacity_adults',
            'capacity_children',
            'total_capacity',
            'description',
            'price',
            'image',
            'availability_status',
            'is_available_now',
        ]



    # ===== LẤY TRẠNG THÁI =====
    def get_availability_status(self, obj):


        # Trả về:
        # Phòng trống / Đã đặt
        return obj.availability_status



    # ===== KIỂM TRA TRỐNG =====
    def get_is_available_now(self, obj):


        # True / False
        return obj.is_available()






# ===== SERIALIZER DANH MỤC PHÒNG =====
class RoomCategorySerializer(serializers.ModelSerializer):


    class Meta:

        model = RoomCategory


        fields = [

            'id',

            'name'
        ]






# ===== SERIALIZER THANH TOÁN =====
class ReservationPaymentSerializer(serializers.ModelSerializer):


    # ===== TÊN PHÒNG =====
    room_name = serializers.CharField(

        source='room.name',

        read_only=True
    )



    # ===== NGÀY TẠO =====
    created_at = serializers.DateTimeField(

        read_only=True
    )



    # ===== THỜI GIAN CHECKOUT =====
    checkout_at = serializers.DateTimeField(

        read_only=True
    )



    # ===== META =====
    class Meta:

        model = Reservation


        fields = [

            'id',
            'room_name',
            'payment_method',
            'payment_status',
            'is_checked_in',
            'checked_in_at',
            'checked_in_adults',
            'checked_in_children',
            'subtotal',
            'gst',
            'deposit_percentage',
            'deposit_amount',
            'balance_due',
            'discount_applied',
            'total',
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'final_total',
            'created_at',
            'checkout_at',
            'deposit_receipt',
            'deposit_receipt_uploaded_at',
            'deposit_confirmed',
        ]






# ===== SERIALIZER UPLOAD BIÊN LAI =====
class UploadDepositReceiptSerializer(serializers.ModelSerializer):


    # ===== FILE UPLOAD =====

    # FileField:
    # upload file ảnh/pdf...
    deposit_receipt = serializers.FileField(

        required=True
    )



    # ===== META =====
    class Meta:

        model = Reservation


        fields = [

            'deposit_receipt'
        ]






# ===== SERIALIZER TÌM KIẾM PHÒNG =====
class RoomSearchSerializer(serializers.Serializer):

    """
    Serializer tìm kiếm phòng
    """


    # ===== NGÀY CHECKIN =====
    check_in_date = serializers.DateField()



    # ===== NGÀY CHECKOUT =====
    check_out_date = serializers.DateField()



    # ===== NGƯỜI LỚN =====
    adults = serializers.IntegerField(

        min_value=1
    )



    # ===== TRẺ EM =====
    children = serializers.IntegerField(

        min_value=0,

        required=False,

        default=0
    )



    # ===== GIỚI HẠN =====
    limit = serializers.IntegerField(

        min_value=1,

        max_value=10,

        required=False,

        default=5
    )



    # ===== VALIDATE =====
    def validate(self, data):


        # Nếu checkout <= checkin
        if data['check_out_date'] <= data['check_in_date']:

            raise serializers.ValidationError(

                "Ngày trả phòng phải sau ngày nhận phòng."
            )



        # Nếu checkin < hôm nay
        if data['check_in_date'] < date.today():

            raise serializers.ValidationError(

                "Ngày nhận phòng không được nhỏ hơn hôm nay."
            )



        # Người lớn <= 0
        if data['adults'] <= 0:

            raise serializers.ValidationError(

                "Số người lớn phải >= 1."
            )



        # Trẻ em < 0
        if data['children'] < 0:

            raise serializers.ValidationError(

                "Số trẻ em không hợp lệ."
            )



        # ===== TỔNG KHÁCH =====
        total_guests = (

            data['adults']

            +

            data['children']
        )



        # Nếu > 10 khách
        if total_guests > 10:

            raise serializers.ValidationError(

                "Tổng số khách không được vượt quá 10 người."
            )



        # Trả dữ liệu hợp lệ
        return data