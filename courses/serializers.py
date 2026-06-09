from rest_framework import serializers
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, SectionChapterControl, ActivityLog, ClassSection, ExtracurricularActivity, SectionActivityControl, HomeworkSubmission
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
        # 🛡️ Esto está perfecto, ya previene que falle si el usuario no está autenticado:
        if request and request.user and request.user.is_authenticated:
            return ClassSection.objects.filter(course=obj, students=request.user).exists()
        return False
    
class ExtracurricularActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtracurricularActivity
        # 👇 Asegúrate de que 'order' esté aquí
        fields = ['id', 'section', 'chapter', 'title', 'section_type', 'due_date', 'content', 'order']

class SectionActivityControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionActivityControl
        # ✅ Asegúrate de incluir 'order' aquí también para que no falle la relación
        fields = ['id', 'section', 'activity', 'is_visible', 'order', 'due_date']

class ClassSectionSerializer(serializers.ModelSerializer):
    course_details = CourseSerializer(source='course', read_only=True)
    extra_activities = ExtracurricularActivitySerializer(many=True, read_only=True)
    activity_controls = SectionActivityControlSerializer(many=True, read_only=True)
    
    total_active_lessons = serializers.SerializerMethodField()
    completed_lessons_count = serializers.SerializerMethodField()
    completed_activities = serializers.SerializerMethodField()
    resume_activity_id = serializers.SerializerMethodField()

    students = serializers.PrimaryKeyRelatedField(many=True, required=False, queryset=User.objects.all())
    teachers = serializers.PrimaryKeyRelatedField(many=True, required=False, queryset=User.objects.all())

    class Meta:
        model = ClassSection
        fields = [
            'id', 'name', 'course', 'course_details', 'is_active', 
            'teachers', 'students', 'show_grades', 'extra_activities', 
            'activity_controls', 'completed_activities', 'resume_activity_id',
            'total_active_lessons', 'completed_lessons_count'
        ]

    def get_completed_activities(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            completed_ids = ActivityLog.objects.filter(
                section=obj, student=request.user, event_type='complete'
            ).values_list('chapter_section', flat=True)
            
            # 🌟 MAGIA: Si el ID es negativo es Extra, si es positivo es Base
            return [f"extra-{abs(cid)}" if cid < 0 else f"base-{cid}" for cid in completed_ids]
        return []
    
    def get_total_active_lessons(self, obj):
        # 🛡️ FIX: Leemos el objeto nativo .activity para extraer su ID de forma inalterable
        visible_base_ids = [
            ctrl.activity.id for ctrl in obj.activity_controls.all() if ctrl.is_visible and ctrl.activity
        ]
        total_extras = obj.extra_activities.count()
        return len(visible_base_ids) + total_extras
    
    def get_completed_lessons_count(self, obj):
        # Mapeamos a los nuevos strings prefijados
        visible_base = [f"base-{ctrl.activity.id}" for ctrl in obj.activity_controls.all() if ctrl.is_visible and ctrl.activity]
        extra_ids = [f"extra-{extra.id}" for extra in obj.extra_activities.all()]
        
        allowed_ids = set(visible_base + extra_ids)
        completed_list = self.get_completed_activities(obj) 
        
        actual_completed = [act_id for act_id in completed_list if act_id in allowed_ids]
        return len(actual_completed)

    def get_resume_activity_id(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0

        completed_logs = self.get_completed_activities(obj)

        ordered_activities = []
        for module in obj.course.modules.all().order_by('order', 'id'):
            for chapter in module.chapters.all().order_by('order', 'id'):
                for section in chapter.sections.all().order_by('order', 'id'):
                    ordered_activities.append(section.id)

        if not ordered_activities:
            return 0 

        if not completed_logs:
            return ordered_activities[0] 

        max_idx = -1
        for comp_id in completed_logs:
            try:
                idx = ordered_activities.index(comp_id)
                if idx > max_idx:
                    max_idx = idx
            except ValueError:
                pass

        if max_idx + 1 < len(ordered_activities):
            return ordered_activities[max_idx + 1]
        
        return ordered_activities[0]   

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'

class StudentPublicProfileSerializer(serializers.ModelSerializer):
    completed_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'completed_count']

    def get_completed_count(self, obj):
        if 'view' in self.context and hasattr(self.context['view'], 'kwargs'):
            section_id = self.context['view'].kwargs.get('pk')
            if section_id:
                # 🛡️ FIX: Cambiamos values().distinct() por un filtro directo count() súper eficiente
                return ActivityLog.objects.filter(
                    section_id=section_id, student=obj, event_type='complete'
                ).count()
        return 0

# 2. Serializador de Perfil Completo (Lo que ve el profesor)
class StudentAnalyticsProfileSerializer(serializers.ModelSerializer):
    completed_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'completed_count']

    def get_completed_count(self, obj):
        if 'view' in self.context and hasattr(self.context['view'], 'kwargs'):
            section_id = self.context['view'].kwargs.get('pk')
            if section_id:
                # 🛡️ FIX: Cambiamos values().distinct() por un filtro directo count() súper eficiente
                return ActivityLog.objects.filter(
                    section_id=section_id, student=obj, event_type='complete'
                ).count()
        return 0

class SectionChapterControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionChapterControl
        fields = '__all__'

class ActivityLogSerializer(serializers.ModelSerializer):
    is_extra = serializers.BooleanField(write_only=True, required=False, default=False)
    class_title = serializers.SerializerMethodField()
    student = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ActivityLog
        # Volvemos a usar 'chapter_section' directamente
        fields = ['id', 'section', 'student', 'chapter_section', 'event_type', 'duration_seconds', 'timestamp', 'is_extra', 'class_title']
    
    def create(self, validated_data):
        validated_data.pop('is_extra', None)
        return super().create(validated_data)

    def get_class_title(self, obj):
        from .models import ChapterSection, ExtracurricularActivity
        try:
            numeric_id = obj.chapter_section # Leemos directo
            if numeric_id is not None:
                if numeric_id > 0:
                    act = ChapterSection.objects.filter(id=numeric_id).first()
                    if act: return act.title
                elif numeric_id < 0:
                    extra = ExtracurricularActivity.objects.filter(id=abs(numeric_id)).first()
                    if extra: return f"Extra: {extra.title}"
        except Exception:
            pass
        return "Actividad o Recurso"
    

class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(write_only=True, required=False) # 🌟 Añadido
    student_name = serializers.SerializerMethodField()
    student_avatar = serializers.SerializerMethodField()

    class Meta:
        model = HomeworkSubmission
        fields = ['id', 'section', 'student', 'student_id', 'student_name', 'student_avatar', 'activity_id', 'content', 'grade', 'feedback', 'submitted_at']
        read_only_fields = ['student', 'student_name', 'student_avatar']

    def create(self, validated_data):
        request = self.context.get('request')
        student_id = validated_data.pop('student_id', None)
        
        if request and request.user.is_teacher and student_id:
            validated_data['student_id'] = student_id
        else:
            validated_data['student'] = request.user
            
        return super().create(validated_data)

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}".strip() or obj.student.username
        
    def get_student_avatar(self, obj):
        return obj.student.first_name[0].upper() if obj.student.first_name else 'U'