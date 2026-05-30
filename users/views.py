from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from django.utils.crypto import get_random_string

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Aquí puedes agregar datos extra al token si lo deseas
        token['username'] = user.username
        token['is_teacher'] = user.is_teacher
        return token

class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

class UserDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            # Si el usuario mandó una nueva contraseña
            if 'password' in request.data and request.data['password']:
                request.user.set_password(request.data['password'])
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GoogleLoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            return Response({'error': 'Token no proporcionado'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Especifica el CLIENT_ID de tu app (configúralo en tu settings.py)
            # settings.GOOGLE_CLIENT_ID = "tu-client-id-de-google.apps.googleusercontent.com"
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )

            email = idinfo['email']
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            avatar = idinfo.get('picture', '')

            # Buscamos si el usuario ya existe
            user = User.objects.filter(email=email).first()

            if not user:
                # Si no existe, lo creamos. Generamos un username único.
                base_username = email.split('@')[0]
                username = f"{base_username}_{str(uuid.uuid4())[:6]}"
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    # CORRECCIÓN: Generamos un string aleatorio seguro de 32 caracteres
                    password=get_random_string(32), 
                    first_name=first_name.title(),
                    last_name=last_name.title(),
                )

            # Generamos los tokens de SimpleJWT para este usuario
            refresh = RefreshToken.for_user(user)
            # Agregamos los claims extra que definiste en tu LoginSerializer original
            refresh['username'] = user.username
            refresh['is_teacher'] = user.is_teacher

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })

        except ValueError:
            # Token inválido o expirado
            return Response({'error': 'Token de Google inválido'}, status=status.HTTP_401_UNAUTHORIZED)