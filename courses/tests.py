from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Course, Module, Chapter, ChapterSection, ClassSection, ActivityLog

User = get_user_model()

class CourseAndSectionSecurityTests(APITestCase):
    
    def setUp(self):
        """
        Configuración inicial: Creamos el ecosistema completo.
        2 Profesores, 2 Estudiantes, 1 Curso, 2 Secciones (grupos).
        """
        # 1. Crear Usuarios
        self.teacher_1 = User.objects.create_user(username='profesor_ariel', password='pw', is_teacher=True, email='ariel@test.com')
        self.teacher_2 = User.objects.create_user(username='profesor_brian', password='pw', is_teacher=True, email='brian@test.com')
        self.student_1 = User.objects.create_user(username='estudiante_carlos', password='pw', is_student=True, email='carlos@test.com')
        self.student_2 = User.objects.create_user(username='estudiante_diana', password='pw', is_student=True, email='diana@test.com')

        # 2. Crear Estructura Base del Curso
        self.course = Course.objects.create(title='Inglés Avanzado', description='Curso de prueba')
        self.module = Module.objects.create(course=self.course, title='Módulo 1', order=1)
        self.chapter = Chapter.objects.create(module=self.module, title='Capítulo 1', order=1)
        self.activity = ChapterSection.objects.create(
            chapter=self.chapter, title='Video Intro', section_type='video', order=1, content={"blocks": []}
        )

        # 3. Crear Secciones (Aislamiento de grupos)
        # Sección A: Le pertenece al Profesor 1 y estudia el Estudiante 1
        self.section_a = ClassSection.objects.create(course=self.course, name='Grupo Mañana')
        self.section_a.teachers.add(self.teacher_1)
        self.section_a.students.add(self.student_1)

        # Sección B: Le pertenece al Profesor 2 y estudia la Estudiante 2
        self.section_b = ClassSection.objects.create(course=self.course, name='Grupo Noche')
        self.section_b.teachers.add(self.teacher_2)
        self.section_b.students.add(self.student_2)

    # ==========================================
    # TESTS DE AUTENTICACIÓN (UNAUTHENTICATED)
    # ==========================================
    def test_unauthenticated_access_is_blocked(self):
        """Si alguien sin login intenta ver las secciones, debe recibir 401."""
        response = self.client.get(f'/api/class-sections/{self.section_a.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ==========================================
    # TESTS DE ESTUDIANTES (STUDENT ACCESS)
    # ==========================================
    def test_student_can_access_enrolled_section(self):
        """Estudiante 1 debe poder ver la Sección A."""
        self.client.force_authenticate(user=self.student_1)
        response = self.client.get(f'/api/class-sections/{self.section_a.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Grupo Mañana')

    def test_student_cannot_access_unenrolled_section(self):
        """Estudiante 1 NO debe poder ver la Sección B. Debe dar 404 (oculto)."""
        self.client.force_authenticate(user=self.student_1)
        response = self.client.get(f'/api/class-sections/{self.section_b.id}/')
        # Esperamos 404 porque el get_queryset filtra lo que no es suyo
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_cannot_edit_section(self):
        """Un estudiante jamás debe poder modificar los detalles de la sección."""
        self.client.force_authenticate(user=self.student_1)
        response = self.client.patch(f'/api/class-sections/{self.section_a.id}/', {'name': 'Hackeado'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # TESTS DE PROFESORES (TEACHER ACCESS)
    # ==========================================
    def test_teacher_can_edit_own_section(self):
        """Profesor 1 puede editar su Sección A."""
        self.client.force_authenticate(user=self.teacher_1)
        response = self.client.patch(f'/api/class-sections/{self.section_a.id}/', {'name': 'Grupo Mañana Modificado'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Grupo Mañana Modificado')

    def test_teacher_cannot_access_other_teacher_section(self):
        """Profesor 1 NO debe poder ver ni editar la Sección B (del Profesor 2)."""
        self.client.force_authenticate(user=self.teacher_1)
        response = self.client.get(f'/api/class-sections/{self.section_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================
    # TESTS DE PRIVACIDAD DE PARTICIPANTES
    # ==========================================
    def test_participants_privacy_for_students(self):
        """Cuando un estudiante ve a sus compañeros, NO debe recibir correos electrónicos."""
        self.client.force_authenticate(user=self.student_1)
        response = self.client.get(f'/api/class-sections/{self.section_a.id}/participants/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_teacher_view'])
        # Validar que la llave 'email' NO existe en el primer estudiante retornado
        self.assertNotIn('email', response.data['participants'][0])

    def test_participants_analytics_for_teachers(self):
        """Cuando un profesor ve a sus estudiantes, SÍ debe recibir correos e información analítica."""
        self.client.force_authenticate(user=self.teacher_1)
        response = self.client.get(f'/api/class-sections/{self.section_a.id}/participants/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_teacher_view'])
        # Validar que la llave 'email' SÍ existe en el primer estudiante retornado
        self.assertIn('email', response.data['participants'][0])

    # ==========================================
    # TESTS DE TELEMETRÍA (ACTIVITY LOGS)
    # ==========================================
    def test_student_creates_activity_log(self):
        """
        Un estudiante envía que abrió un video.
        Validamos que el backend asigne al estudiante correcto IGNORANDO si el frontend mandó otro ID.
        """
        self.client.force_authenticate(user=self.student_1)
        payload = {
            'section': self.section_a.id,
            'chapter_section': self.activity.id,
            'event_type': 'open',
            'duration_seconds': 45
        }
        response = self.client.post('/api/activity-logs/', payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Validar en base de datos
        log = ActivityLog.objects.first()
        self.assertEqual(log.student, self.student_1) # Quedó registrado al estudiante 1
        self.assertEqual(log.duration_seconds, 45)

    def test_teacher_views_student_analytics(self):
        """Un profesor pide el resumen de actividad de un estudiante en su sección."""
        # Creamos un log manual
        ActivityLog.objects.create(
            student=self.student_1, section=self.section_a, chapter_section=self.activity,
            event_type='complete', duration_seconds=120
        )
        
        self.client.force_authenticate(user=self.teacher_1)
        response = self.client.get(f'/api/class-sections/{self.section_a.id}/student-analytics/{self.student_1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_time_seconds'], 120)
        self.assertEqual(len(response.data['activity_logs']), 1)