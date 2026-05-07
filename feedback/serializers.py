from rest_framework import serializers
from .models import Feedback
from rooms.models import Reservation, Room


class FeedbackSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.name', read_only=True)
    booking_code = serializers.CharField(source='reservation.booking_code', read_only=True, allow_null=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = [
            'id',
            'user_name',
            'email',
            'room',
            'room_name',
            'reservation',
            'booking_code',
            'country',
            'rating',
            'comment',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'room_name', 'booking_code', 'user_name']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return obj.name


class FeedbackCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating feedback after checkout"""
    booking_code = serializers.CharField(required=True, write_only=True)  # Use booking code to find reservation

    class Meta:
        model = Feedback
        fields = [
            'booking_code',
            'name',
            'email',
            'country',
            'rating',
            'comment',
        ]

    def validate_booking_code(self, value):
        """Validate and get the reservation from booking code"""
        try:
            # Extract the ID from booking code (e.g., "BK000123" -> 123)
            reservation_id = int(value.replace('BK', ''))
            reservation = Reservation.objects.get(id=reservation_id)
            return reservation
        except (Reservation.DoesNotExist, ValueError):
            raise serializers.ValidationError("Invalid booking code.")

    def create(self, validated_data):
        reservation = validated_data.pop('booking_code')
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None

        feedback = Feedback.objects.create(
            reservation=reservation,
            room=reservation.room,
            user=user,
            **validated_data
        )
        return feedback


class FeedbackListSerializer(serializers.ModelSerializer):
    """Serializer for listing feedback with minimal info"""
    room_name = serializers.CharField(source='room.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    stars = serializers.CharField(source='get_rating_display', read_only=True)

    class Meta:
        model = Feedback
        fields = [
            'id',
            'user_name',
            'room_name',
            'rating',
            'comment',
            'created_at',
            'stars',
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return obj.name or "Anonymous"
