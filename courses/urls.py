from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (CourseViewSet, ModuleViewSet, ChapterViewSet, 
                    ChapterSectionViewSet, ClassSectionViewSet, GradeViewSet,
                    SectionChapterControlViewSet, ActivityLogViewSet)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'chapters', ChapterViewSet)
router.register(r'chapter-sections', ChapterSectionViewSet)
router.register(r'class-sections', ClassSectionViewSet)
router.register(r'grades', GradeViewSet)
router.register(r'chapter-controls', SectionChapterControlViewSet)
router.register(r'activity-logs', ActivityLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]