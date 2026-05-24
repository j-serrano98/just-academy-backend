from rest_framework import serializers
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade

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