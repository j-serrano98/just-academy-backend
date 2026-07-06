import threading
from exponent_server_sdk import PushClient, PushMessage
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

# 🚀 Ajusta estas importaciones según dónde tengas tus modelos finalmente
from courses.models import Notification, SectionActivityControl

User = get_user_model()

def _execute_instant_notification(user_id, notif_type, title, message, target_url):
    """Función interna que se ejecuta en segundo plano."""
    try:
        user = User.objects.get(id=user_id)
        
        # 1. Guardar en base de datos
        Notification.objects.create(
            user=user,
            notification_type=notif_type,
            title=title,
            message=message,
            target_url=target_url
        )
        
        # 2. Enviar Push a Expo
        if user.expo_push_token:
            PushClient().publish(
                PushMessage(
                    to=user.expo_push_token,
                    title=title,
                    body=message,
                    data={"url": target_url}
                )
            )
    except Exception as e:
        print(f"❌ Error en hilo de notificación: {e}")

def send_instant_notification(user_id, notif_type, title, message, target_url):
    """Lanza el hilo asíncrono para no bloquear al usuario."""
    thread = threading.Thread(
        target=_execute_instant_notification,
        args=(user_id, notif_type, title, message, target_url)
    )
    thread.daemon = True
    thread.start()

def check_due_assignments():
    """Escanea tareas por vencer. Lo llamaremos desde un endpoint."""
    today = timezone.now().date()
    target_dates = [
        today + timedelta(days=1), 
        today + timedelta(days=2), 
        today + timedelta(days=3)
    ]
    
    upcoming_activities = SectionActivityControl.objects.filter(
        due_date__date__in=target_dates,
        is_visible=True
    ).select_related('section', 'activity')
    
    total_sent = 0
    for control in upcoming_activities:
        days_left = (control.due_date.date() - today).days
        students = control.section.students.all()
        
        for student in students:
            has_submitted = student.submissions.filter(
                section=control.section, 
                activity_id=control.activity.id
            ).exists()
            
            if not has_submitted:
                send_instant_notification(
                    user_id=student.id,
                    notif_type='DUE_SOON',
                    title=f'¡Vence en {days_left} día(s)! ⏰',
                    message=f'La actividad "{control.activity.title}" está por cerrar.',
                    target_url=f'/course/{control.section.id}?activityId=base-{control.activity.id}'
                )
                total_sent += 1
                
    return total_sent