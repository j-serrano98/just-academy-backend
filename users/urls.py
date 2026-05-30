from django.urls import path
from .views import RegisterView, UserDetailView, LoginView, GoogleLoginView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('profile/', UserDetailView.as_view(), name='profile'),
]