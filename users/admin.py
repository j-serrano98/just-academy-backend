from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Roles de Plataforma', {'fields': ('is_teacher', 'is_student')}),
    )
    list_display = ['username', 'email', 'is_teacher', 'is_student', 'is_staff']

admin.site.register(User, CustomUserAdmin)