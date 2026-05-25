from rest_framework import serializers
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, SectionChapterControl, ActivityLog, ClassSection, ExtracurricularActivity, SectionActivityControl
from django.contrib.auth import get_user_model
from users.models import User
User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    # Traemos las secciones donde el usuario está inscrito
    enrolled_sections = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'enrolled_sections']

    def get_enrolled_sections(self, obj):
        # Buscamos todas las secciones donde este usuario sea estudiante
        sections = ClassSection.objects.filter(students=obj)
        return [{"id": s.id, "name": s.name, "course_name": s.course.title} for s in sections]

class ChapterSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterSection
        # ¡AQUÍ ESTÁ LA MAGIA! Faltaba agregar 'chapter' a esta lista
        fields = ['id', 'chapter', 'title', 'content', 'section_type', 'order']

class ChapterSerializer(serializers.ModelSerializer):
    # Esto es crucial: asegúrate de que 'module' sea un PrimaryKeyRelatedField o simplemente 
    # permite que el ViewSet lo asigne automáticamente.
    sections = ChapterSectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Chapter
        fields = ['id', 'module', 'title', 'sections', 'order']

class CourseDetailSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    class Meta:
        model = Course
        fields = ['id', 'title', 'chapters']

class ModuleSerializer(serializers.ModelSerializer):
    # El related_name en el modelo debe ser 'chapters'
    chapters = ChapterSerializer(many=True, read_only=True)
    
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'chapters', 'order']

class PublicSectionSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ClassSection
        fields = ['id', 'name', 'is_active', 'max_students', 'students_count']
        
    def get_students_count(self, obj):
        return obj.students.count()
    
class CourseSerializer(serializers.ModelSerializer):
    # ESTA ES LA LÍNEA MÁGICA QUE FALTABA:
    modules = ModuleSerializer(many=True, read_only=True) 
    
    is_enrolled = serializers.SerializerMethodField()
    
    # (Asumiendo que tienes el PublicSectionSerializer de pasos anteriores)
    class_sections = PublicSectionSerializer(many=True, read_only=True) 

    class Meta:
        model = Course
        fields = '__all__'

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
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
    
    # NUEVOS CAMPOS:
    completed_activities = serializers.SerializerMethodField()
    resume_activity_id = serializers.SerializerMethodField()

    students = serializers.PrimaryKeyRelatedField(many=True, required=False, queryset=User.objects.all())
    teachers = serializers.PrimaryKeyRelatedField(many=True, required=False, queryset=User.objects.all())

    class Meta:
        model = ClassSection
        fields = ['id', 'name', 'course', 'course_details', 'is_active', 'teachers', 'students', 'show_grades', 'extra_activities', 'activity_controls', 'completed_activities', 'resume_activity_id']

    def get_completed_activities(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Trae todos los IDs de actividades completadas por este alumno en este grupo
            return list(ActivityLog.objects.filter(
                section=obj, student=request.user, event_type='complete'
            ).values_list('chapter_section_id', flat=True))
        return []

    def get_resume_activity_id(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0

        completed_logs = self.get_completed_activities(obj)

        # Aplanamos el temario para obtener una lista ordenada de TODAS las actividades
        ordered_activities = []
        for module in obj.course.modules.all().order_by('order', 'id'):
            for chapter in module.chapters.all().order_by('order', 'id'):
                for section in chapter.sections.all().order_by('order', 'id'):
                    ordered_activities.append(section.id)

        if not ordered_activities:
            return 0 # El curso no tiene contenido

        if not completed_logs:
            return ordered_activities[0] # No ha hecho nada, mandarlo a la primera

        # LÓGICA INTELIGENTE: Buscar el índice máximo completado
        max_idx = -1
        for comp_id in completed_logs:
            try:
                idx = ordered_activities.index(comp_id)
                if idx > max_idx:
                    max_idx = idx
            except ValueError:
                pass

        # Devolver la que sigue después de la última completada (saltándose huecos)
        if max_idx + 1 < len(ordered_activities):
            return ordered_activities[max_idx + 1]
        
        # Si ya completó todo el curso, lo mandamos a la primera
        return ordered_activities[0]


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
        fields = ['id', 'name', 'course', 'course_details', 'is_active', 'teachers', 'students', 'show_grades', 'extra_activities', 'activity_controls', 'completed_activities', 'resume_activity_id']

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

