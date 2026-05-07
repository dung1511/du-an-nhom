from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User

from rest_framework import serializers

from .models import Coupon, Reservation, Room, RoomCategory, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "slug", "description", "price", "image", "image_url", "active", "order"]


class ReservationCreateSerializer(serializers.ModelSerializer):
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(), source="room", write_only=True
    )
    user_id = serializers.IntegerField(required=False, write_only=True)
    email = serializers.EmailField(required=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Reservation
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

        if not room.can_accommodate(adults=adults, children=children):
            raise serializers.ValidationError(
                (
                    f"Phong chi cho toi da {room.total_capacity} khach "
                    f"({room.capacity_adults} nguoi lon, {room.capacity_children} tre em)."
                )
            )

        if not room.is_available(check_in, check_out):
            raise serializers.ValidationError("Phong da duoc dat trong khoang thoi gian nay.")

        request = self.context.get("request")
        actor = getattr(request, "user", None)
        user_id = attrs.pop("user_id", None)
        if user_id is not None:
            if not actor or not actor.is_authenticated or not (actor.is_staff or actor.is_superuser):
                raise serializers.ValidationError("Chi staff/admin moi co the gan booking cho nguoi dung khac.")
            try:
                attrs["user"] = User.objects.get(pk=user_id)
            except User.DoesNotExist as exc:
                raise serializers.ValidationError("Nguoi dung khong ton tai.") from exc
        elif actor and actor.is_authenticated and not (actor.is_staff or actor.is_superuser):
            attrs["user"] = actor

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

        reservation = Reservation(**validated_data)
        reservation.sync_financial_fields()
        reservation.save()
        return reservation


class ReservationCheckInSerializer(serializers.Serializer):
    booking_code = serializers.CharField(required=True)
    checked_in_adults = serializers.IntegerField(min_value=1)
    checked_in_children = serializers.IntegerField(min_value=0, required=False, default=0)
    actual_check_in_date = serializers.DateField(required=False, allow_null=True)  # Ngày check-in thực tế (có thể sớm)

    def validate(self, attrs):
        try:
            reservation_id = Reservation.get_reservation_id_from_booking_code(attrs['booking_code'])
        except ValueError as exc:
            raise serializers.ValidationError({'booking_code': str(exc)}) from exc

        try:
            reservation = Reservation.objects.select_related('room').get(id=reservation_id)
        except Reservation.DoesNotExist as exc:
            raise serializers.ValidationError({'booking_code': 'Không tìm thấy booking tương ứng.'}) from exc

        if reservation.is_checked_out:
            raise serializers.ValidationError('Booking này đã check-out.')

        if reservation.is_checked_in:
            raise serializers.ValidationError('Booking này đã check-in trước đó.')

        actual_check_in_date = attrs.get('actual_check_in_date')
        if actual_check_in_date:
            # Cho phép check-in từ 7 ngày trước ngày đặt phòng
            min_early_checkin = reservation.check_in_date - timedelta(days=7)
            if actual_check_in_date < min_early_checkin:
                raise serializers.ValidationError(
                    f'Chỉ có thể check-in sớm tối đa 7 ngày (từ {min_early_checkin})'
                )
            # Không thể check-in sau ngày dự kiến
            if actual_check_in_date > reservation.check_in_date:
                raise serializers.ValidationError(
                    'Ngày check-in thực tế không được muộn hơn ngày check-in dự kiến'
                )
        else:
            # Nếu không cung cấp, dùng ngày check-in dự kiến
            if date.today() < reservation.check_in_date:
                raise serializers.ValidationError('Chưa tới ngày check-in của booking.')
            actual_check_in_date = reservation.check_in_date

        checked_in_adults = attrs.get('checked_in_adults', 0)
        checked_in_children = attrs.get('checked_in_children', 0)
        checked_in_total = checked_in_adults + checked_in_children
        booked_total = (reservation.adults or 0) + (reservation.children or 0)

        if checked_in_total > booked_total:
            raise serializers.ValidationError('Số khách đến check-in vượt quá số khách đã đặt.')

        if not reservation.room.can_accommodate(
            adults=checked_in_adults,
            children=checked_in_children,
        ):
            raise serializers.ValidationError('Số khách đến check-in vượt quá sức chứa của phòng.')

        attrs['reservation'] = reservation
        attrs['actual_check_in_date'] = actual_check_in_date
        return attrs



class ReservationCheckoutSerializer(serializers.ModelSerializer):
    """Serializer để xử lý trả phòng (checkout)"""
    room_name = serializers.CharField(source='room.name', read_only=True)
    checkout_date = serializers.DateField(source='check_out_date', read_only=True)
    checkout_at = serializers.DateTimeField(read_only=True)
    damage_reported = serializers.BooleanField(required=False, default=False)
    damage_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Reservation
        fields = [
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
            'damage_reported',
            'damage_notes',
            'damage_fee',
            'final_total',
            'payment_status',
            'is_checked_out',
            'checkout_at',
        ]
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

    def update(self, instance, validated_data):
        damage_reported = validated_data.pop('damage_reported', False)
        damage_notes = validated_data.pop('damage_notes', '') or ''

        instance.is_checked_out = True
        if not instance.checkout_at:
            instance.checkout_at = datetime.now()
        instance.damage_reported = bool(damage_reported)
        instance.damage_notes = damage_notes
        instance.damage_fee = instance.calculate_damage_fee() if instance.damage_reported else Decimal('0.00')
        instance.final_total = instance.total + instance.damage_fee
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
    selected_services = ServiceSerializer(many=True, read_only=True)
    num_nights = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
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
    created_at = serializers.DateTimeField(read_only=True)
    checkout_at = serializers.DateTimeField(read_only=True)

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


class UploadDepositReceiptSerializer(serializers.ModelSerializer):
    # Use FileField to accept uploads even when Pillow is not available in test env
    deposit_receipt = serializers.FileField(required=True)

    class Meta:
        model = Reservation
        fields = ['deposit_receipt']


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
