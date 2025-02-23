from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, VerificationCode, PasswordResetToken
import logging

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'is_verified', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        logger.info(f"Validating email: {value}")  # Use logging instead of print
        return value

    def create(self, validated_data):
        logger.info("Validating data: %s", validated_data)  # Use logging
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class VerificationCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationCode
        fields = ['code', 'created_at', 'expires_at']


class PasswordResetTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordResetToken
        fields = ['token', 'created_at', 'expires_at']
