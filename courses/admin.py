from django.contrib import admin
from .models import Course, Module, Chapter, ChapterSection, ClassSection, Grade, SectionChapterControl, ActivityLog, Notification

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
admin.site.register(Notification)

@admin.register(SectionChapterControl)
class SectionChapterControlAdmin(admin.ModelAdmin):
    list_display = ('section', 'chapter', 'is_visible', 'due_date')
    list_filter = ('section', 'is_visible')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'event_type', 'chapter_section', 'timestamp')
    list_filter = ('event_type', 'section')
    search_fields = ('student__username', 'student__email')