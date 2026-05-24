from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsTeacher, IsTeacherOfSectionOrReadOnly
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, ClassSection, SectionChapterControl, ActivityLog
from .serializers import (CourseSerializer, ModuleSerializer, ChapterSerializer, 
                          ChapterSectionSerializer, ClassSectionSerializer, GradeSerializer,
                          ClassSectionSerializer, SectionChapterControlSerializer, 
                          ActivityLogSerializer, StudentPublicProfileSerializer, 
                          StudentAnalyticsProfileSerializer)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    # 1. ARCHIVAR CURSO
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        course = self.get_object()
        course.is_archived = not course.is_archived # Cambia el estado
        course.save()
        status_text = "archivado" if course.is_archived else "desarchivado"
        return Response({'status': f'Curso {status_text} correctamente'})

    # 2. DUPLICAR CURSO (Lógica profunda)
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        original_course = self.get_object()
        
        # Copiar curso
        new_course = Course.objects.create(
            title=f"{original_course.title} (Copia)",
            description=original_course.description
        )

        # Copiar Módulos, Capítulos y Secciones
        for module in original_course.modules.all():
            new_module = Module.objects.create(course=new_course, title=module.title, order=module.order)
            
            for chapter in module.chapters.all():
                new_chapter = Chapter.objects.create(module=new_module, title=chapter.title, order=chapter.order)
                
                for section in chapter.sections.all():
                    ChapterSection.objects.create(
                        chapter=new_chapter, 
                        title=section.title, 
                        section_type=section.section_type,
                        content=section.content,
                        order=section.order
                    )
                    
        serializer = self.get_serializer(new_course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # NUEVO: Endpoint para inscribirse a un curso
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        user = request.user
        
        # Para simplificar, buscamos o creamos una sección general para este curso
        section, created = ClassSection.objects.get_or_create(
            course=course,
            name=f"Grupo General - {course.title}",
            defaults={'is_active': True}
        )
        
        # Añadimos al usuario a los estudiantes de esta sección
        section.students.add(user)
        return Response({'status': 'Inscrito correctamente', 'section_id': section.id}, status=status.HTTP_200_OK)

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer

class ChapterSectionViewSet(viewsets.ModelViewSet):
    queryset = ChapterSection.objects.all()
    serializer_class = ChapterSectionSerializer

class ClassSectionViewSet(viewsets.ModelViewSet):
    queryset = ClassSection.objects.prefetch_related('students', 'teachers', 'course')
    serializer_class = ClassSectionSerializer
    permission_classes = [IsAuthenticated, IsTeacherOfSectionOrReadOnly]

    def get_queryset(self):
        """
        Filtro de seguridad a nivel de base de datos.
        Un usuario JAMÁS podrá consultar una sección a la que no pertenece.
        """
        user = self.request.user
        if user.is_teacher:
            return self.queryset.filter(teachers=user)
        return self.queryset.filter(students=user)

    # ENDPOINT PARA LISTAR ESTUDIANTES CON PRIVACIDAD CONDICIONAL
    @action(detail=True, methods=['get'], url_path='participants')
    def participants(self, request, pk=None):
        section = self.get_object() # get_object() ya valida que pertenezcan a la sección gracias a get_queryset()
        students = section.students.all()
        
        # Si es profesor, mandamos toda la analítica
        if request.user.is_teacher:
            serializer = StudentAnalyticsProfileSerializer(students, many=True)
            return Response({'is_teacher_view': True, 'participants': serializer.data})
        
        # Si es estudiante, mandamos la versión censurada (solo nombres/avatares)
        serializer = StudentPublicProfileSerializer(students, many=True)
        return Response({'is_teacher_view': False, 'participants': serializer.data})

    # ENDPOINT PARA QUE EL PROFESOR VEA EL ANALYTICS DE UN ALUMNO EN ESTA SECCIÓN
    @action(detail=True, methods=['get'], url_path='student-analytics/(?P<student_id>\d+)', permission_classes=[IsAuthenticated, IsTeacher])
    def student_analytics(self, request, pk=None, student_id=None):
        section = self.get_object()
        
        # Verificar si el profesor enseña esta sección
        if not section.teachers.filter(id=request.user.id).exists():
            return Response({"error": "No tienes permisos de profesor en esta sección"}, status=403)
            
        logs = ActivityLog.objects.filter(section=section, student_id=student_id)
        serializer = ActivityLogSerializer(logs, many=True)
        
        # Aquí puedes agregar lógica para sumar el duration_seconds total, sacar promedios de quizzes, etc.
        total_time = sum(log.duration_seconds for log in logs)
        
        return Response({
            "total_time_seconds": total_time,
            "activity_logs": serializer.data
        })

class SectionChapterControlViewSet(viewsets.ModelViewSet):
    queryset = SectionChapterControl.objects.all()
    serializer_class = SectionChapterControlSerializer
    permission_classes = [IsAuthenticated, IsTeacher] # Solo profesores pueden manipular la visibilidad

class ActivityLogViewSet(viewsets.ModelViewSet):
    """
    Endpoint para que el Frontend envíe telemetría (logs) de lo que hace el estudiante.
    """
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Un profesor puede ver los logs de sus secciones, un estudiante solo los suyos
        user = self.request.user
        if user.is_teacher:
            sections = ClassSection.objects.filter(teachers=user)
            return self.queryset.filter(section__in=sections)
        return self.queryset.filter(student=user)

    def perform_create(self, serializer):
        """
        SEGURIDAD CRÍTICA: Forzamos que el creador del log sea el usuario que hace la petición.
        El frontend no puede enviar "student_id=2" si el que está logueado es el 1.
        """
        serializer.save(student=self.request.user)

class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer