# core/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from exponent_server_sdk import PushClient, PushMessage
from courses.models import Notification
from courses.models import SectionActivityControl, ClassSection
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_instant_notification(user_id, notif_type, title, message, target_url):
    """ Tarea asíncrona para guardar y enviar una notificación push """
    try:
        user = User.objects.get(id=user_id)
        
        # 1. Guardar en la base de datos (Para el panel In-App)
        Notification.objects.create(
            user=user,
            notification_type=notif_type,
            title=title,
            message=message,
            target_url=target_url
        )
        
        # 2. Enviar a los servidores de Expo si el usuario tiene el token configurado
        if user.expo_push_token:
            PushClient().publish(
                PushMessage(
                    to=user.expo_push_token,
                    title=title,
                    body=message,
                    data={"url": target_url}
                )
            )
    except User.DoesNotExist:
        pass

@shared_task
def check_due_assignments():
    """ Tarea programada (Celery Beat) para buscar tareas a punto de vencer """
    today = timezone.now().date()
    
    # Queremos avisar cuando falten exactamente 1, 2 o 3 días
    target_dates = [
        today + timedelta(days=1), 
        today + timedelta(days=2), 
        today + timedelta(days=3)
    ]
    
    # Buscar controles de actividad que venzan en esas fechas exactas
    upcoming_activities = SectionActivityControl.objects.filter(
        due_date__date__in=target_dates,
        is_visible=True
    ).select_related('section', 'activity')
    
    for control in upcoming_activities:
        days_left = (control.due_date.date() - today).days
        
        # Obtener todos los estudiantes de esta sección
        students = control.section.students.all()
        
        for student in students:
            # Verificar si el estudiante YA envió la tarea
            has_submitted = student.submissions.filter(
                section=control.section, 
                activity_id=control.activity.id
            ).exists()
            
            if not has_submitted:
                send_instant_notification.delay(
                    user_id=student.id,
                    notif_type='DUE_SOON',
                    title=f'¡Vence en {days_left} día(s)! ⏰',
                    message=f'La actividad "{control.activity.title}" está por cerrar.',
                    target_url=f'/course/{control.section.id}?activityId=base-{control.activity.id}'
                )