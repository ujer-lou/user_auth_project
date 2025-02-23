import logging
import random

from celery import shared_task
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import User, VerificationCode, PasswordResetToken
from .serializers import UserSerializer
from .tasks import delete_verification_code

logger = logging.getLogger(__name__)


@shared_task
def send_verification_email(user_id, code):
    user = User.objects.get(id=user_id)
    subject = 'Verify Your Email'
    message = f'Use this code to verify your email: {code}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=True)


class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        logger.info("Request data: %s", request.data)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            expires_at = timezone.now() + timezone.timedelta(minutes=5)
            verification_code = VerificationCode.objects.create(
                user=user,
                code=code,
                expires_at=expires_at
            )
            # Schedule deletion task
            delete_verification_code.apply_async(
                args=[verification_code.id],
                eta=verification_code.expires_at
            )
            send_verification_email.delay(user.id, code)
            return Response({
                'message': 'User registered. Check your email for verification code.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        logger.error("Serializer errors: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class RegisterView(generics.CreateAPIView):
#     serializer_class = UserSerializer
#     permission_classes = [AllowAny]
#
#     def create(self, request, *args, **kwargs):
#         logger.info("Request data: %s", request.data)
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             # For testing, we use a fixed code
#             code = '123456'
#             expires_at = timezone.now() + timezone.timedelta(minutes=5)
#             verification_code = VerificationCode.objects.create(
#                 user=user,
#                 code=code,
#                 expires_at=expires_at
#             )
#             # Schedule deletion task
#             delete_verification_code.apply_async(
#                 args=[verification_code.id],
#                 eta=verification_code.expires_at
#             )
#             send_verification_email.delay(user.id, code)
#             # Return the verification_code in the response for testing.
#             return Response({
#                 'message': 'User registered. Check your email for verification code.',
#                 'user_id': user.id,
#                 'verification_code': code
#             }, status=status.HTTP_201_CREATED)
#         logger.error("Serializer errors: %s", serializer.errors)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        code = request.data.get('code')
        try:
            user = User.objects.get(id=user_id)
            verification_code = VerificationCode.objects.get(user=user, code=code)
            if verification_code.expires_at < timezone.now():
                return Response({'error': 'Verification code expired.'}, status=status.HTTP_400_BAD_REQUEST)
            user.is_verified = True
            user.save()
            verification_code.delete()
            return Response({'message': 'Email verified successfully.'}, status=status.HTTP_200_OK)
        except (User.DoesNotExist, VerificationCode.DoesNotExist):
            return Response({'error': 'Invalid user or verification code.'}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)
        if user and user.is_verified:
            login(request, user)
            return Response({'message': 'Login successful.'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid credentials or email not verified.'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timezone.timedelta(hours=1)
            )
            # Send password reset email (simplified for now, use Celery for async later)
            subject = 'Password Reset Request'
            message = f'Use this token to reset your password: {token.token}'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]
            send_mail(subject, message, from_email, recipient_list, fail_silently=True)
            return Response({'message': 'Password reset link sent to your email.'}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)


# class PasswordResetRequestView(generics.GenericAPIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request, *args, **kwargs):
#         email = request.data.get('email')
#         try:
#             user = User.objects.get(email=email)
#             # Create a new token (unique due to the model's default)
#             token_obj = PasswordResetToken.objects.create(
#                 user=user,
#                 expires_at=timezone.now() + timezone.timedelta(hours=1)
#             )
#             # Use the generated unique token
#             subject = 'Password Reset Request'
#             message = f'Use this token to reset your password: {token_obj.token}'
#             from_email = settings.EMAIL_HOST_USER
#             recipient_list = [user.email]
#             send_mail(subject, message, from_email, recipient_list, fail_silently=True)
#             # Return the unique token for testing purposes
#             return Response({
#                 'message': 'Password reset link sent to your email.',
#                 'reset_token': str(token_obj.token)
#             }, status=status.HTTP_200_OK)
#         except User.DoesNotExist:
#             return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token_str = request.data.get('token')
        new_password = request.data.get('new_password')
        try:
            token = PasswordResetToken.objects.get(token=token_str)
            if token.expires_at < timezone.now():
                return Response({'error': 'Token expired.'}, status=status.HTTP_400_BAD_REQUEST)
            user = token.user
            user.set_password(new_password)
            user.save()
            token.delete()
            return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
