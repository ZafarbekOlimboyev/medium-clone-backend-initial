from random import random
from rest_framework import status, permissions, generics, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer, LoginSerializer, UserUpdateSerializer, ValidationErrorSerializer, TokenResponseSerializer
from .enums import TokenType
from .services import SendEmailService, TokenService, UserService
from django.contrib.auth import get_user_model, update_session_auth_hash
from django_redis import get_redis_connection
from rest_framework.exceptions import ValidationError

from .serializers import UserSerializer, LoginSerializer, ValidationErrorSerializer, TokenResponseSerializer, ChangePasswordSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

User = get_user_model()

# SignUp qilish uchun class
@extend_schema_view(
    post=extend_schema(
        summary="Sign up a new user",
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: ValidationErrorSerializer
        }
    )
)
class SignupView(APIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            return Response({
                'user': user_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Login qilish uchun class
@extend_schema_view(
    post=extend_schema(
        summary="Log in a user",
        request=LoginSerializer,
        responses={
            200: TokenResponseSerializer,
            400: ValidationErrorSerializer,
        }
    )
)
class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Hisob maʼlumotlari yaroqsiz'}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema_view(
    post=extend_schema(
        summary="Log out a user",
        request=None,
        responses={
            200: ValidationErrorSerializer,
            401: ValidationErrorSerializer
        }
    )
)
class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=None)
    def post(self, request, *args, **kwargs):
        UserService.create_tokens(request.user, access='fake_token', refresh='fake_token', is_force_add_to_redis=True)
        return Response({"detail": "Mufaqqiyatli chiqildi."})


# User malumotlarni olish uchum class
@extend_schema_view(
    get=extend_schema(
        summary="Get user information",
        responses={
            200: UserSerializer,
            400: ValidationErrorSerializer
        }
    ),
    patch=extend_schema(                   # user malumotlarni yangilash uchun patch qo'shildi
        summary="Update user information",
        request=UserUpdateSerializer,
        responses={
            200: UserUpdateSerializer,
            400: ValidationErrorSerializer
        }
    )
)
class UsersMe(generics.RetrieveAPIView, generics.UpdateAPIView):
    http_method_names = ['get', 'patch']             # patch qo'shildi
    queryset = User.objects.filter(is_active=True)
    parser_classes = [parsers.MultiPartParser]       # fayl yuklash uchun MultiPartParser qo'shildi
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    
    def get_serializer_class(self): 

        email = self.request.user.email
        code = random.randint(10000, 99999)
        SendEmailService.send_email(email, code)            # email jo'natish uchun
         
        if self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer

    def patch(self, request, *args, **kwargs):
        redis_conn = get_redis_connection('default')
        redis_conn.set('test_key', 'test_value', ex=3600)
        cached_value = redis_conn.get('test_key')
        print(cached_value)

        return super().partial_update(request, *args, **kwargs)


@extend_schema_view(
    put=extend_schema(
        summary="Change user password",
        request=ChangePasswordSerializer,
        responses={
            200: TokenResponseSerializer,
            401: ValidationErrorSerializer
        }
    )
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def put(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=request.user.username,
            password=serializer.validated_data['old_password']
        )

        if user is not None:
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            update_session_auth_hash(request, user)
            tokens = UserService.create_tokens(user, is_force_add_to_redis=True)
            return Response(tokens)
        else:
            raise ValidationError("Eski parol xato.")
