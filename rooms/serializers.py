from datetime import date
from decimal import Decimal

from rest_framework import serializers

from .models import Coupon, Reservation, Room, RoomCategory


class ReservationCreateSerializer(serializers.ModelSerializer):
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(), source="room", write_only=True
    )
    coupon_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "room_id",
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
            "discount_applied",
            "total",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "room",
            "subtotal",
            "gst",
            "discount_applied",
            "total",
            "payment_status",
            "created_at",
        ]

    def validate(self, attrs):
        room = attrs["room"]
        check_in = attrs.get("check_in_date")
        check_out = attrs.get("check_out_date")
        adults = attrs.get("adults", 1)
        children = attrs.get("children", 0)

        if not check_in or not check_out:
            raise serializers.ValidationError("Vui long cung cap ngay check-in va check-out.")

        if check_in < date.today():
            raise serializers.ValidationError("Ngay check-in khong duoc nho hon hom nay.")

        if check_out <= check_in:
            raise serializers.ValidationError("Ngay check-out phai sau ngay check-in.")

        if adults <= 0:
            raise serializers.ValidationError("So nguoi lon phai lon hon 0.")

        if children < 0:
            raise serializers.ValidationError("So tre em khong hop le.")

        if adults + children > room.capacity:
            raise serializers.ValidationError(
                f"Phong chi cho toi da {room.capacity} khach."
            )

        if not room.is_available(check_in, check_out):
            raise serializers.ValidationError("Phong da duoc dat trong khoang thoi gian nay.")

        coupon_code = attrs.pop("coupon_code", "").strip()
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    code=coupon_code,
                    active=True,
                    valid_from__lte=date.today(),
                    valid_to__gte=date.today(),
                )
            except Coupon.DoesNotExist:
                raise serializers.ValidationError("Ma giam gia khong hop le hoac da het han.")

        attrs["coupon"] = coupon
        return attrs

    def create(self, validated_data):
        room = validated_data["room"]
        check_in = validated_data["check_in_date"]
        check_out = validated_data["check_out_date"]
        coupon = validated_data.pop("coupon", None)

        num_nights = (check_out - check_in).days
        subtotal = room.price * num_nights
        gst = subtotal * Decimal("0.18")

        discount = Decimal("0.00")
        if coupon:
            discount = (subtotal * coupon.discount_percentage) / Decimal("100")

        total = subtotal + gst - discount

        validated_data["subtotal"] = subtotal
        validated_data["gst"] = gst
        validated_data["discount_applied"] = discount
        validated_data["total"] = total
        validated_data["coupon"] = coupon

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["user"] = request.user

        return Reservation.objects.create(**validated_data)


class ReservationCheckoutSerializer(serializers.ModelSerializer):
    """Serializer để xử lý trả phòng (checkout)"""
    room_name = serializers.CharField(source='room.name', read_only=True)
    checkout_date = serializers.DateField(source='check_out_date', read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            'id',
            'room_name',
            'check_in_date',
            'check_out_date',
            'checkout_date',
            'user',
            'first_name',
            'last_name',
            'email',
            'phone',
            'total',
            'payment_status',
            'is_checked_out',
        ]
        read_only_fields = [
            'id',
            'room_name',
            'check_in_date',
            'check_out_date',
            'checkout_date',
            'user',
            'first_name',
            'last_name',
            'email',
            'phone',
            'total',
            'payment_status',
        ]

    def update(self, instance, validated_data):
        instance.is_checked_out = True
        instance.save()
        return instance


class ReservationDetailSerializer(serializers.ModelSerializer):
    """Serializer để xem chi tiết đặt phòng"""
    room_name = serializers.CharField(source='room.name', read_only=True)
    room_price = serializers.DecimalField(
        source='room.price', 
        max_digits=10, 
        decimal_places=2,
        read_only=True
    )
    num_nights = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
        fields = [
            'id',
            'room_name',
            'room_price',
            'check_in_date',
            'check_out_date',
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
            'discount_applied',
            'total',
            'payment_method',
            'payment_status',
            'is_checked_out',
            'created_at',
        ]
    
    def get_num_nights(self, obj):
        if obj.check_in_date and obj.check_out_date:
            return (obj.check_out_date - obj.check_in_date).days
        return 0


class ReturnedReservationSerializer(serializers.ModelSerializer):
    room = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    num_nights = serializers.SerializerMethodField()
    total_guests = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id',
            'room',
            'user',
            'coupon_code',
            'check_in_date',
            'check_out_date',
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
            'discount_applied',
            'total',
            'payment_method',
            'payment_status',
            'is_checked_out',
            'created_at',
        ]

    def get_user(self, obj):
        if not obj.user:
            return None

        profile = getattr(obj.user, 'profile', None)
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'email': obj.user.email,
            'phone_number': profile.phone_number if profile else None,
        }

    def get_room(self, obj):
        return RoomSerializer(obj.room).data

    def get_num_nights(self, obj):
        if obj.check_in_date and obj.check_out_date:
            return (obj.check_out_date - obj.check_in_date).days
        return 0

    def get_total_guests(self, obj):
        return (obj.adults or 0) + (obj.children or 0)


class RoomSerializer(serializers.ModelSerializer):
    """Serializer cho Room - hiển thị thông tin phòng"""
    availability_status = serializers.SerializerMethodField()
    is_available_now = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            'id',
            'name',
            'category',
            'capacity',
            'size',
            'capacity_adults',
            'capacity_children', 
            'total_capacity',
            'description',
            'price',
            'image',
            'availability_status',
            'is_available_now',
        ]

    def get_availability_status(self, obj):
        return obj.availability_status

    def get_is_available_now(self, obj):
        return obj.is_available()


class RoomCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomCategory
        fields = ['id', 'name']


class ReservationPaymentSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id',
            'room_name',
            'payment_method',
            'payment_status',
            'subtotal',
            'gst',
            'discount_applied',
            'total',
            'created_at',
        ]


class RoomSearchSerializer(serializers.Serializer):
    """Serializer cho tìm kiếm phòng và đề xuất"""
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    adults = serializers.IntegerField(min_value=1)
    children = serializers.IntegerField(min_value=0, required=False, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=10, required=False, default=5)
    
    def validate(self, data):
        """Xác thực dữ liệu tìm kiếm"""
        if data['check_out_date'] <= data['check_in_date']:
            raise serializers.ValidationError(
                "Ngày trả phòng phải sau ngày nhận phòng."
            )
        
        if data['check_in_date'] < date.today():
            raise serializers.ValidationError(
                "Ngày nhận phòng không được nhỏ hơn hôm nay."
            )
        
        if data['adults'] <= 0:
            raise serializers.ValidationError(
                "Số người lớn phải >= 1."
            )
        
        if data['children'] < 0:
            raise serializers.ValidationError(
                "Số trẻ em không hợp lệ."
            )
        
        total_guests = data['adults'] + data['children']
        if total_guests > 10:
            raise serializers.ValidationError(
                "Tổng số khách không được vượt quá 10 người."
            )
        
        return data
