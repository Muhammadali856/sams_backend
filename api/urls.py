from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssignmentViewSet, TaskViewSet 
from .views import UpdateStudentProgrammesView, ProgrammeViewSet, StudentViewSet, QuizViewSet

# IMPORT OUR NEW VIEWS HERE:
from .views import CustomLoginView, ChangePasswordView
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()

router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'programmes', ProgrammeViewSet, basename='programme')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'quizzes', QuizViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
    
    # WE DELETED SIGNUP AND REPLACED THE LOGIN URL:
    path('auth/login/', CustomLoginView.as_view(), name='custom_login'), 
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/update-programmes/', UpdateStudentProgrammesView.as_view(), name='update-programmes'),
]