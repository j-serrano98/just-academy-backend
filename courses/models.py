from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
User = get_user_model()

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    thumbnail = models.URLField(max_length=800, blank=True, null=True)
    
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Chapter(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

class ChapterSection(models.Model):
    SECTION_TYPES = (
        ('video', 'Video'),
        ('reading', 'Lectura'),
        ('exercise', 'Ejercicio'),
        ('quiz', 'Quiz'),
        ('game', 'Juego'),
        ('practice', 'Práctica'),
        ('manual_task', 'Tarea Manual'),
    )
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, default='video')
    content = models.JSONField(default=dict, blank=True) # Para guardar JSONs como el de Interchange
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} ({self.get_section_type_display()})"

class ClassSection(models.Model):
    """ Esta es la sección donde se imparte el curso a un grupo específico """
    name = models.CharField(max_length=255) # Ej: "Inglés 1 - Lunes Noche"
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='class_sections')
    teachers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='teaching_sections', limit_choices_to={'is_teacher': True})
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='enrolled_sections', limit_choices_to={'is_student': True})
    max_students = models.IntegerField(default=0, help_text="0 significa sin límite de cupo")
    show_grades = models.BooleanField(default=False) # Visibilidad de calificaciones deshabilitada por defecto
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Grade(models.Model):
    """ Calificaciones de las tareas/quizzes de un estudiante en una sección específica """
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grades')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='grades')
    chapter_section = models.ForeignKey(ChapterSection, on_delete=models.CASCADE) # La actividad evaluada
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.chapter_section.title}: {self.score}"
    
class SectionChapterControl(models.Model):
    """Controla qué capítulos están visibles y sus fechas límite por sección."""
    section = models.ForeignKey('ClassSection', on_delete=models.CASCADE, related_name='chapter_controls')
    chapter = models.ForeignKey('Chapter', on_delete=models.CASCADE)
    is_visible = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('section', 'chapter') # Un capítulo no puede tener dos controles en la misma sección

    def __str__(self):
        return f"{self.chapter.title} - {self.section.name}"

class ActivityLog(models.Model):
    """Registro inmutable de lo que hace el estudiante (Trazabilidad)."""
    EVENT_CHOICES = (
        ('open', 'Opened Activity'),
        ('complete', 'Completed Activity'),
        ('quiz_submit', 'Submitted Quiz'),
        ('time_heartbeat', 'Time Heartbeat'), # Para contar tiempo
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    section = models.ForeignKey('ClassSection', on_delete=models.CASCADE)
    chapter_section = models.ForeignKey('ChapterSection', on_delete=models.CASCADE) # La actividad específica
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    duration_seconds = models.IntegerField(default=0, help_text="Tiempo invertido en esta sesión de actividad")
    metadata = models.JSONField(null=True, blank=True) # Para guardar notas del quiz (ej: {"score": 80})
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', 'section']), # Optimización para consultas analíticas
        ]

class ExtracurricularActivity(models.Model):
    """Actividades exclusivas de la sección anidadas dentro del temario."""
    section = models.ForeignKey('ClassSection', on_delete=models.CASCADE, related_name='extra_activities')
    
    # Agregamos null=True, blank=True para que Django no se queje con las tareas viejas
    chapter = models.ForeignKey('Chapter', on_delete=models.CASCADE, related_name='extra_activities', null=True, blank=True)

    order = models.IntegerField(default=0)
    
    title = models.CharField(max_length=200)
    section_type = models.CharField(max_length=50, choices=ChapterSection.SECTION_TYPES, default='exercise')
    content = models.JSONField(default=dict, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SectionActivityControl(models.Model):
    """Controla la visibilidad y fechas límite de las actividades del curso maestro en una sección específica."""
    section = models.ForeignKey('ClassSection', on_delete=models.CASCADE, related_name='activity_controls')
    activity = models.ForeignKey('ChapterSection', on_delete=models.CASCADE)
    
    # Cambiamos is_unlocked a is_visible para que funcione con los botones de "ojito" del frontend
    is_visible = models.BooleanField(default=False) 
    order = models.IntegerField(default=0, null=True, blank=True)
    
    due_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('section', 'activity')

class SectionCustomTask(models.Model):
    """Tareas, ejercicios o material exclusivo de esta sección (no afecta al curso maestro)."""
    section = models.ForeignKey('ClassSection', on_delete=models.CASCADE, related_name='custom_tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=50, choices=(
        ('assignment', 'Entrega de Tarea'),
        ('reading', 'Material de Lectura'),
        ('zoom', 'Clase en Vivo (Link)'),
    ))
    due_date = models.DateTimeField(null=True, blank=True)
    url_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)