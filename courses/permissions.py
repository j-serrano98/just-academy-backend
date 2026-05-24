from rest_framework import permissions

class IsTeacher(permissions.BasePermission):
    """Permite el acceso solo a usuarios con el flag is_teacher."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_teacher)

class IsTeacherOfSectionOrReadOnly(permissions.BasePermission):
    """
    Profesores de la sección pueden editar. 
    Estudiantes de la sección pueden leer. 
    Nadie más puede hacer nada.
    """
    def has_object_permission(self, request, view, obj):
        # Asegurarnos de que el usuario está autenticado
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Si es un método seguro (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            # ¿Es estudiante de esta sección o profesor de esta sección?
            return obj.students.filter(id=request.user.id).exists() or obj.teachers.filter(id=request.user.id).exists()
            
        # Si es método de escritura (PUT, PATCH, DELETE)
        return request.user.is_teacher and obj.teachers.filter(id=request.user.id).exists()