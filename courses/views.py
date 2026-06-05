from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum
from django.contrib.auth import get_user_model
from .permissions import IsTeacher, IsTeacherOfSectionOrReadOnly
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, ClassSection, SectionChapterControl, ActivityLog, ExtracurricularActivity, SectionActivityControl
from .serializers import (CourseSerializer, ModuleSerializer, ChapterSerializer, 
                          ChapterSectionSerializer, ClassSectionSerializer, GradeSerializer,
                          ClassSectionSerializer, SectionChapterControlSerializer, 
                          ActivityLogSerializer, StudentPublicProfileSerializer, 
                          StudentAnalyticsProfileSerializer, ExtracurricularActivitySerializer)



class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        """
        Permite que cualquier usuario (incluso anónimo) vea los cursos,
        pero exige autenticación para inscribirse, archivar o duplicar.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

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
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        section_id = request.data.get('section_id') # Esperamos un ID numérico o la palabra 'async'
        
        # 1. VERIFICAR INSCRIPCIÓN DOBLE
        if ClassSection.objects.filter(course=course, students=request.user).exists():
            return Response({'error': 'Ya estás inscrito en este curso en otro grupo.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 2. MANEJAR MODALIDAD ASÍNCRONA (AUTODIDACTA)
        if section_id == 'async':
            # Buscamos o creamos el grupo "Autodidacta" para este curso
            section, created = ClassSection.objects.get_or_create(
                course=course,
                name="Modalidad Asíncrona (A tu propio ritmo)",
                defaults={'is_active': True, 'max_students': 0, 'show_grades': False}
            )
        
        # 3. MANEJAR GRUPOS REGULARES (SÁBADOS, ETC)
        else:
            try:
                section = ClassSection.objects.get(id=section_id, course=course, is_active=True)
            except ClassSection.DoesNotExist:
                return Response({'error': 'El grupo seleccionado no existe o está cerrado.'}, status=status.HTTP_404_NOT_FOUND)
                
            # Verificar Cupos
            if section.max_students > 0 and section.students.count() >= section.max_students:
                return Response({'error': 'Este grupo ya no tiene cupos disponibles.'}, status=status.HTTP_400_BAD_REQUEST)
                
        # 4. INSCRIBIR AL ALUMNO
        section.students.add(request.user)
        
        return Response({
            'message': f'¡Inscripción exitosa en: {section.name}!',
            'section_id': section.id
        }, status=status.HTTP_200_OK)
    
    def get_queryset(self):
        # 🛡️ Validamos primero si el usuario está autenticado antes de preguntar si es profesor
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_teacher:
            return Course.objects.all()
            
        # Si es un estudiante o un visitante público anónimo, SOLO LOS PUBLICADOS
        return Course.objects.filter(is_published=True, is_archived=False)

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
    
    # def list(self, request, *args, **kwargs):
    #     try:
    #         # Forzamos la ejecución real de la query SQL evaluando el queryset en una lista
    #         queryset = self.filter_queryset(self.get_queryset())
    #         page = self.paginate_queryset(queryset)
    #         if page is not None:
    #             serializer = self.get_serializer(page, many=True)
    #             return self.get_paginated_response(serializer.data)

    #         serializer = self.get_serializer(queryset, many=True)
    #         return Response(serializer.data)
    #     except Exception as e:
    #         # 🚨 ESTA ES LA MAGIA: Imprime el error exacto de Python/Postgres en los logs de Render
    #         print("\n" + "="*50)
    #         print("🚨 ERROR CRÍTICO DETECTADO EN CLASS-SECTIONS:")
    #         import traceback
    #         traceback.print_exc()
    #         print("="*50 + "\n")
            
    #         # Devolvemos el error detallado al frontend para leerlo desde la consola del navegador
    #         return Response(
    #             {"error_debug": str(e), "traceback": traceback.format_exc()}, 
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

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
    
    @action(detail=True, methods=['post'], url_path='toggle-visibility')
    def toggle_visibility(self, request, pk=None):
        section = self.get_object()
        entity_type = request.data.get('entity_type') # 'module', 'chapter', 'activity'
        entity_id = request.data.get('entity_id')
        is_visible = request.data.get('is_visible', False)

        activities = []
        if entity_type == 'module':
            module = Module.objects.get(id=entity_id)
            for chapter in module.chapters.all():
                activities.extend(list(chapter.sections.all()))
        elif entity_type == 'chapter':
            chapter = Chapter.objects.get(id=entity_id)
            activities.extend(list(chapter.sections.all()))
        elif entity_type == 'activity':
            activities.append(ChapterSection.objects.get(id=entity_id))

        for act in activities:
            control, _ = SectionActivityControl.objects.get_or_create(section=section, activity=act)
            control.is_visible = is_visible
            control.save()

        return Response({'status': 'ok'})

    @action(detail=True, methods=['post'], url_path='set-due-date')
    def set_due_date(self, request, pk=None):
        section = self.get_object()
        activity_id = request.data.get('activity_id')
        due_date = request.data.get('due_date') # Recibe un string ISO o None
        
        act = ChapterSection.objects.get(id=activity_id)
        control, _ = SectionActivityControl.objects.get_or_create(section=section, activity=act)
        control.due_date = due_date if due_date else None
        control.save()
        
        return Response({'status': 'ok'})
    
    @action(detail=True, methods=['post'], url_path='toggle-completion', permission_classes=[IsAuthenticated])
    def toggle_completion(self, request, pk=None):
        section = self.get_object()
        activity_id = request.data.get('activity_id')
        is_completed = request.data.get('is_completed', True)
        
        try:
            activity = ChapterSection.objects.get(id=activity_id)
            
            if is_completed:
                # CORRECCIÓN AQUÍ: Incluimos event_type='complete' en la BÚSQUEDA, no en el default
                ActivityLog.objects.get_or_create(
                    section=section,
                    student=request.user,
                    chapter_section=activity,
                    event_type='complete', # <-- AHORA SÍ BUSCARÁ SOLO LOS COMPLETADOS
                    defaults={'duration_seconds': 0}
                )
            else:
                # Borramos el registro si el alumno decide desmarcarla
                ActivityLog.objects.filter(
                    section=section,
                    student=request.user,
                    chapter_section=activity,
                    event_type='complete'
                ).delete()
                
            return Response({'status': 'ok'})
            
        except ChapterSection.DoesNotExist:
            return Response({'error': 'La actividad no existe.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # 🌟 TU ACCIÓN PERSONALIZADA DE REORDENAMIENTO:
    @action(detail=True, methods=['post'], url_path='reorder-chapter')
    def reorder_chapter(self, request, pk=None):
        """
        Endpoint personalizado para intercalar el orden de clases base y extras
        """
        items = request.data.get('items', [])
        
        try:
            for item in items:
                item_id = item.get('id')
                item_type = item.get('type')
                new_order = item.get('order')

                if item_type == 'base':
                    # get_or_create maneja la existencia o creación del registro de control
                    control, _ = SectionActivityControl.objects.get_or_create(
                        section_id=pk, 
                        activity_id=item_id  # Cámbialo si tu llave foránea tiene otro nombre
                    )
                    control.order = new_order
                    control.save()

                elif item_type == 'extra':
                    try:
                        extra = ExtracurricularActivity.objects.get(id=item_id)
                        extra.order = new_order
                        extra.save()
                    except ExtracurricularActivity.DoesNotExist:
                        continue 

            return Response({"status": "ok"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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


class ExtracurricularActivityViewSet(viewsets.ModelViewSet):
    queryset = ExtracurricularActivity.objects.all()
    serializer_class = ExtracurricularActivitySerializer
    permission_classes = [IsAuthenticated, IsTeacher]

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny]) # 🌟 Hacemos que sea público para la landing page
def global_stats(request):
    """
    Calcula las estadísticas en tiempo real para la landing page de Just Academy.
    """
    try:
        # 1. Total de estudiantes únicos registrados que no sean staff/profesores
        total_students = User.objects.filter(is_staff=False, is_superuser=False).count()
        
        # 2. Total de profesores registrados (o que estén asignados a alguna sección)
        # Puedes ajustarlo según cómo identifiques a tus profesores en tu modelo de User
        total_teachers = User.objects.filter(is_staff=True).count() 
        if total_teachers == 0:
            # Fallback por si manejas profesores mediante la relación en ClassSection
            total_teachers = User.objects.filter(classsection__isnull=False).distinct().count()

        # 3. Total de cursos publicados y activos
        total_courses = Course.objects.filter(is_published=True, is_archived=False).count()

        # 4. Total de horas de clase simuladas o sumadas (puedes ajustar el cálculo según tus campos)
        # Como fallback o si no tienes un campo de horas nativo, calculamos una métrica basada 
        # en 10 horas estimadas por cada módulo o sección del temario activo.
        total_hours = 0
        courses = Course.objects.filter(is_published=True, is_archived=False)
        for course in courses:
            # Contamos cuántas lecciones (ChapterSection) tiene el curso
            lessons_count = sum(chapter.sections.count() for module in course.modules.all() for chapter in module.chapters.all())
            # Asumimos una media de 1.5 horas por lección/ejercicio
            total_hours += max(lessons_count * 1.5, 10) # Mínimo 10 horas por curso

        return Response({
            "students": f"{total_students}+" if total_students > 0 else "10+",
            "courses": f"{total_courses}+" if total_courses > 0 else "1+",
            "teachers": f"{total_teachers}+" if total_teachers > 0 else "1+",
            "hours": f"{int(total_hours)}+" if total_hours > 0 else "20+",
        })
    except Exception as e:
        # Fallback seguro en caso de que alguna tabla esté vacía durante pruebas
        return Response({
            "students": "10+",
            "courses": "1+",
            "teachers": "1+",
            "hours": "20+"
        })