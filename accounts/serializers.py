from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Profile
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name')

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    def to_representation(self, instance):
        profile = instance
        user = profile.user
        return {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone_number': profile.phone_number,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
        }

    def update(self, instance, validated_data):
        user = instance.user

        for field in ['first_name', 'last_name', 'email']:
            if field in validated_data:
                setattr(user, field, validated_data[field])
        user.save()

        for field in ['phone_number', 'profile_picture']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not value:
            raise serializers.ValidationError('Vui lòng nhập mật khẩu hiện tại.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({'confirm_new_password': 'Mật khẩu xác nhận không khớp.'})
        validate_password(attrs['new_password'])
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'is_staff',
            'date_joined',
            'phone_number',
        ]

    def get_phone_number(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.phone_number if profile else None