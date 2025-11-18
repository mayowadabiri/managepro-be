from rest_framework import viewsets
from user.models import User, Code, UserProvider, Type
from .serializers import UserSerializers
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from django.contrib.auth import authenticate
from django.contrib.auth import login
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from google.oauth2 import id_token
from google.auth.transport import requests
from django.db import transaction
from core.notification import send_email
from core.secrets import hash_otp
import hmac

MAX_ATTEMPTS = 5


def invalid_credentials():
    return Response(
        {
            "message": "Invalid user or pasword",
            "code": "ACCOUNT_DOES_NOT_MATCH",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


def generic_otp_error():
    return Response(
        {"message": "Invalid or expired code", "code": "INVALID_EXPIRED_OTP"},
        status=status.HTTP_400_BAD_REQUEST,
    )


class AuthViewset(viewsets.ModelViewSet):
    serializer_class = UserSerializers
    permission_classes = [AllowAny]
    authentication_classes = []

    class Incoming(serializers.Serializer):
        email = serializers.EmailField()
        password = serializers.CharField(max_length=16)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        code = user.generate_user_code()
        send_email(
            to=user.email,
            variables={
                "id": "email-verification-otp",
                "variables": {
                    "NAME": f"{user.first_name} {user.last_name}",
                    "OTP_CODE": code,
                },
            },
        )
        return Response(
            {"message": "User created Sucessfully"}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False, methods=["post"], url_path="verify-email", url_name="verify-email"
    )
    def validate_email(self, request):
        email = (request.data.get("email") or "").strip()
        code_input = (request.data.get("code") or "").strip()

        # quick input validation
        if not email or not code_input:
            return Response(
                {"message": "Email and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response(
                {"message": "User does not exist, Please try again"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        with transaction.atomic():
            candidate = (
                user.otp_code.filter(type=Type.REGISTRATION, is_used=False)
                .order_by("-created_at")
                .select_for_update()
                .first()
            )
            if candidate is None:
                return generic_otp_error()

            if now > candidate.expires_at:
                candidate.is_used = True
                candidate.used_at = now
                candidate.save(update_fields=["is_used", "used_at"])
                return generic_otp_error()

            # Check attempts limit
            if candidate.attempts >= MAX_ATTEMPTS:
                candidate.is_used = True
                candidate.used_at = now
                candidate.save(update_fields=["is_used", "used_at"])
                return generic_otp_error()

            # Hash & constant-time compare
            input_hash = hash_otp(str(code_input))
            if not hmac.compare_digest(input_hash, candidate.code_hash):
                candidate.attempts += 1
                # Revoke if reached max attempts after increment
                if candidate.attempts >= MAX_ATTEMPTS:
                    candidate.is_used = True
                    candidate.used_at = now
                    candidate.save(update_fields=["attempts", "is_used", "used_at"])
                else:
                    candidate.save(update_fields=["attempts"])
                return generic_otp_error()

            # Success: mark used and verify user
            candidate.is_used = True
            candidate.used_at = now
            candidate.attempts += 1
            candidate.save(update_fields=["is_used", "used_at", "attempts"])

            user.is_verified = True
            user.save(update_fields=["is_verified"])

        send_email(
            user.email,
            variables={
                "id": "register-email",
                "variables": {"NAME": f"{user.first_name} {user.last_name}"},
            },
        )

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
        email = request.data.get("email").strip()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response(
                {"message": "User does not exist, Please try again"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        with transaction.atomic():
            latest_code = (
                user.otp_code.filter(type=Type.REGISTRATION)
                .order_by("-created_at")
                .select_for_update()
                .first()
            )

            if latest_code and not latest_code.is_used and latest_code.expires_at > now:
                latest_code.delete()

            new_code = user.generate_user_code()
            send_email(
                to=user.email,
                variables={
                    "id": "email-verification-otp",
                    "variables": {
                        "NAME": f"{user.first_name} {user.last_name}",
                        "OTP_CODE": new_code,
                    },
                },
            )
        return Response(
            {"message": "Resend Successful"}, status=status.HTTP_201_CREATED
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="login",
        url_name="login",
    )
    def login(self, request):
        srlz = self.Incoming(data=request.data)
        if srlz.is_valid():
            email = srlz.data.get("email")
            password = srlz.data.get("password")
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                return invalid_credentials()
            if not user.is_verified:
                return Response(
                    {
                        "message": "Email address is not verified, try agaon",
                        "code": "ACCOUNT_DOES_NOT_MATCH",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = authenticate(username=email, password=password)
            if user is None:
                return invalid_credentials()
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            Token.objects.filter(user=user).delete()
            token, _ = Token.objects.get_or_create(user=user)
            response = Response({"token": token.key})

            return response

    @action(
        detail=False,
        methods=["post"],
        url_path="google-login",
        url_name="login_google",
    )
    def loginByGoogle(self, request):
        credential = request.data.get("credential", None)

        google_request = requests.Request()
        user_info = id_token.verify_oauth2_token(
            credential, request=google_request, audience=settings.GOOGLE_CLIENT_ID
        )
        print(user_info)
        email = user_info.get("email")

        with transaction.atomic():
            user = User.objects.select_for_update().filter(email__iexact=email).first()

            if user is None:
                user_data = {
                    "first_name": user_info.get("given_name"),
                    "last_name": user_info.get("family_name"),
                    "email": email,
                    "is_verified": True,
                    "image_url": user_info.get("picture"),
                }
                new_user = User.objects.create(**user_data)
                proivder_payload = {
                    "provider": "google",
                    "provider_id": user_info["sub"],
                    "provider_email": email,
                }
                UserProvider.objects.create(user_id=new_user, **proivder_payload)
                token, _ = Token.objects.get_or_create(user=new_user)
                send_email(
                    user.email,
                    variables={
                        "id": "register-email",
                        "variables": {"NAME": f"{user.first_name} {user.last_name}"},
                    },
                )
                return Response({"token": token.key})

            has_google = user.user_provider.filter(provider="google").exists()

            if not has_google:
                return Response(
                    {
                        "code": "ACCOUNT_EXISTS_NEEDS_LINKING",
                        "message": "An account with this email already exists. Link it.",
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            Token.objects.filter(user=user).delete()
            token, _ = Token.objects.get_or_create(user=user)

            return Response({"token": token.key})

    @action(
        detail=False,
        methods=["post"],
        url_path="link-google",
        url_name="link-google",
    )
    def linkAccountWithGoogle(self, request):
        password = request.data.get("password")
        credential = request.data.get("credential")
        google_request = requests.Request()
        user_info = id_token.verify_oauth2_token(
            credential, request=google_request, audience=settings.GOOGLE_CLIENT_ID
        )
        email = user_info["email"]
        user = authenticate(username=email, password=password)
        if user is None:
            return Response(
                {"message": "Invalid user/password", "code": "ACCOUNT_DOES_NOT_EXIST"},
                status=status.HTTP_404_NOT_FOUND,
            )
        proivder_payload = {
            "provider": "google",
            "provider_id": user_info["sub"],
            "provider_email": email,
            "user_id": user,
            "linked_at": timezone.now(),
        }
        UserProvider.objects.create(
            **proivder_payload,
        )
        user.image_url = user_info["picture"]
        user.last_login = timezone.now()
        user.save(update_fields=["image_url", "last_login"])
        Token.objects.filter(user=user).delete()
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"token": token.key})


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializers
    queryset = User.objects.all()

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
