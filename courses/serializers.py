from rest_framework import serializers
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, SectionChapterControl, ActivityLog, ClassSection
from users.models import User

class ChapterSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterSection
        fields = '__all__'

class ChapterSerializer(serializers.ModelSerializer):
    sections = ChapterSectionSerializer(many=True, read_only=True)
    class Meta:
        model = Chapter
        fields = '__all__'

class ModuleSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    class Meta:
        model = Course
        fields = '__all__'

class ClassSectionSerializer(serializers.ModelSerializer):
    # Esto creará el objeto 'course_details' que el frontend necesita para leer .title y .description
    course_details = CourseSerializer(source='course', read_only=True)

    class Meta:
        model = ClassSection
        fields = ['id', 'name', 'course', 'course_details', 'is_active', 'teachers', 'students']

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'

class StudentPublicProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name'] # NUNCA exponer email ni logs aquí

# 2. Serializador de Perfil Completo (Lo que ve el profesor)
class StudentAnalyticsProfileSerializer(serializers.ModelSerializer):
    # Podrías agregar campos calculados aquí más adelante (ej. tiempo_total)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class SectionChapterControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionChapterControl
        fields = '__all__'

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ['student', 'timestamp']