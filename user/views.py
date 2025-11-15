from rest_framework import viewsets
from user.models import User, Code
from .serializers import UserSerializers
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from user.utils import send_system_email
from django.contrib.auth import authenticate
from django.contrib.auth import login
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta
from rest_framework.permissions import IsAuthenticated, AllowAny
from google.oauth2 import id_token
from google.auth.transport import requests


class AuthViewset(viewsets.ModelViewSet):
    serializer_class = UserSerializers
    permission_classes = [AllowAny]

    class Incoming(serializers.Serializer):
        email = serializers.EmailField()
        password = serializers.CharField(max_length=16)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        code = user.generate_user_code()
        email = serializer.data.get("email")
        message = f"Hi there, thanks for registering with us! Your verification code is {code.code}."
        subject = "Welcome to ManagePro 🎉"
        # send_system_email(email, message=message, subject=subject)

        return Response(
            {"message": "User created Sucessfully"}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False, methods=["post"], url_path="verify-email", url_name="verify-email"
    )
    def validate_email(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response(
                {"message": "User does not exist, Please try again"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        code = request.data.get("code")
        user_code = Code.objects.filter(code=code).first()
        if user_code is None:
            return Response({"message": "Code does not exist, please try again"})
        if user_code.is_used:
            return Response({"message": "This OTP code is already used."})
        expires_at = user_code.expires_at
        now = timezone.now()
        user_code.used_at = timezone.now()
        user_code.is_used = True
        user.is_verified = True
        if now > expires_at:
            user_code.save()
            return Response(
                {"message": "This code has expired. Please request a new one."}
            )
        user_code.is_used = True
        user_code.save()
        user.save()
        return Response(
            {"message": "Email verified successfully"}, status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=["put"],
        url_path="resend-otp-code",
        url_name="resend-otp-code",
    )
    def resend_otp(self, request):
        email = request.data.get("email")
        subject = "Verify your email address"
        user = User.objects.filter(email__iexact=email).first()
        latest_code = Code.objects.filter(user=user).order_by("-created_at").first()
        now = timezone.now()
        if latest_code and latest_code.expires_at > now and not latest_code.is_used:
            message = f"Hi there, your new code is {latest_code.code}."
            send_system_email(email=email, message=message, subject=subject)
        else:
            new_code = user.generate_user_code()
            message = f"Hi there, your new code is {new_code.code}."
            send_system_email(email=email, message=message, subject=subject)

        return Response(
            {"message": "Resend Successful"}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="login",
        url_name="login",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def login(self, request):
        srlz = self.Incoming(data=request.data)
        if srlz.is_valid():
            email = srlz.data.get("email")
            password = srlz.data.get("password")
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                return Response(
                    {"message": "Invalid user/password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not user.is_verified:
                return Response(
                    {"message": "Email address is not verified, try agaon"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = authenticate(username=email, password=password)
            if user is None:
                return Response(
                    {"message": "Invalid user/password"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Token.objects.filter(user=user).delete()
            token, _ = Token.objects.get_or_create(user=user)
            response = Response({"token": token.key})

            return response

    @action(
        detail=False, methods=["post"], url_path="google-login", url_name="login_google"
    )
    def loginByGoogle(self, request):
        credential = request.data.get("credential", None)
        google_request = requests.Request()
        user_info = id_token.verify_oauth2_token(
            credential, request=google_request, audience=settings.GOOGLE_CLIENT_ID
        )
        email = user_info.get("email")

        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            # Create New User
            user_data = {
                "provider_id": user_info.get("sub"),
                "provider": "google",
                "first_name": user_info.get("given_name"),
                "last_name": user_info.get("family_name"),
                "email": email,
                "is_verified": True,
                "image_url": user_info.get("picture"),
            }
            new_user = User.objects.create(**user_data)
            token, _ = Token.objects.get_or_create(user=new_user)
            return Response({"token": token.key})

        if user.provider != "google":
            # User provider is local
            return Response(
                {
                    "code": "ACCOUNT_EXISTS_NEEDS_LINKING",
                    "message": "An account with this email already exists. Link it by entering your password or verify via email.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        Token.objects.filter(user=user).delete()
        token, _ = Token.objects.get_or_create(user=user)
        response = Response({"token": token.key})
        return response


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializers
    queryset = User.objects.all()

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
