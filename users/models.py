from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=True) 
    
    avatar = models.URLField(max_length=800, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({'Teacher' if self.is_teacher else 'Student'})"