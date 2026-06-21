from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssignmentViewSet, TaskViewSet 
from .views import UpdateStudentSubjectsView, SubjectViewSet, StudentViewSet, QuizViewSet
from . import views

from .views import CustomLoginView, ChangePasswordView, StudentProfileSettingsView, create_student_account
from .views import RequestPasswordResetOTPView, VerifyPasswordResetOTPView, ConfirmPasswordResetView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import TriggerDeadlineEmailsView

router = DefaultRouter()

router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'students', StudentViewSet, basename='student')
router.register(r'quizzes', QuizViewSet, basename='quiz')

urlpatterns = [
    
    path('students/create/', create_student_account, name='create-student'),
    path('', include(router.urls)),
    
    path('auth/login/', CustomLoginView.as_view(), name='custom_login'), 
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/<int:pk>/', StudentProfileSettingsView.as_view(), name='profile-settings'),
    path('teachers/create/', views.create_staff_teacher, name='create-staff-teacher'),
    path('auth/forgot-password/request/', RequestPasswordResetOTPView.as_view(), name='fp-request'),
    path('auth/forgot-password/verify/', VerifyPasswordResetOTPView.as_view(), name='fp-verify'),
    path('auth/forgot-password/confirm/', ConfirmPasswordResetView.as_view(), name='fp-confirm'),
    path('cron/send-reminders/', TriggerDeadlineEmailsView.as_view(), name='cron-send-reminders'),
    path('students/create/', create_student_account, name='create-student'),
]