from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Roles de Plataforma', {'fields': ('is_teacher', 'is_student')}),
        ('Configuración Móvil (Expo)', {'fields': ('expo_push_token',)}),
    )
    
    list_display = ['username', 'email', 'is_teacher', 'is_student', 'is_staff', 'expo_push_token']
    search_fields = ['username', 'email', 'expo_push_token']

admin.site.register(User, CustomUserAdmin)