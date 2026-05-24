from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade
from .serializers import (CourseSerializer, ModuleSerializer, ChapterSerializer, 
                          ChapterSectionSerializer, ClassSectionSerializer, GradeSerializer)

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
    queryset = ClassSection.objects.all()
    serializer_class = ClassSectionSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_sections(self, request):
        if request.user.is_teacher:
            sections = self.queryset.filter(teachers=request.user)
        else:
            sections = self.queryset.filter(students=request.user)
            
        serializer = self.get_serializer(sections, many=True)
        return Response(serializer.data)

class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer