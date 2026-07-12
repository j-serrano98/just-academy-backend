from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views import RegisterView, UserDetailView
from courses.views import google_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('courses.urls')),
    
    # Endpoints de Autenticación
    path('api/auth/register/', RegisterView.as_view(), name='auth_register'), 
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/me/', UserDetailView.as_view(), name='auth_me'),
    path('api/auth/google/', google_login, name='google-login'),
    path('api/users/', include('users.urls')),
]