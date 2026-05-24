from django.contrib import admin
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_archived', 'created_at')
    list_filter = ('is_archived',)
    search_fields = ('title',)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'order')

@admin.register(ChapterSection)
class ChapterSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'section_type', 'order')
    list_filter = ('section_type',)

@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'show_grades', 'is_active')
    filter_horizontal = ('teachers', 'students') # Interfaz limpia para seleccionar múltiples usuarios

admin.site.register(Grade)