from rest_framework import serializers
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, SectionChapterControl, ActivityLog, ClassSection, ExtracurricularActivity, SectionActivityControl
from django.contrib.auth import get_user_model
from users.models import User
User = get_user_model()

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
    is_enrolled = serializers.SerializerMethodField()
    modules = ModuleSerializer(many=True, read_only=True) # Asumiendo que tienes esto

    class Meta:
        model = Course
        fields = '__all__'

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Verifica si el estudiante está en ALGUNA sección de este curso
            return ClassSection.objects.filter(course=obj, students=request.user).exists()
        return False
    
class ExtracurricularActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtracurricularActivity
        fields = '__all__'

class SectionActivityControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionActivityControl
        fields = '__all__'

class ClassSectionSerializer(serializers.ModelSerializer):
    course_details = CourseSerializer(source='course', read_only=True)


    extra_activities = ExtracurricularActivitySerializer(many=True, read_only=True)
    activity_controls = SectionActivityControlSerializer(many=True, read_only=True)

    # 3. Pasamos User.objects.all() al queryset para que DRF pueda validar los IDs
    students = serializers.PrimaryKeyRelatedField(
        many=True, 
        required=False, 
        queryset=User.objects.all()
    )
    
    teachers = serializers.PrimaryKeyRelatedField(
        many=True, 
        required=False, 
        queryset=User.objects.all()
    )

    class Meta:
        model = ClassSection
        fields = ['id', 'name', 'course', 'course_details', 'is_active', 'teachers', 'students', 'show_grades', 'extra_activities', 'activity_controls']

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

