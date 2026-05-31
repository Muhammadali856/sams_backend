from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Subject, Assignment, Task, Student, Teacher, Quiz
from .serializers import AssignmentSerializer, TaskSerializer
from .serializers import StudentSerializer, RegisterStudentSerializer, SubjectSerializer, QuizSerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomLoginSerializer, ChangePasswordSerializer, StudentProfileSettingsSerializer

# 1. View to handle our custom 3-field login
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomLoginSerializer

# 2. View to handle changing the default password
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            # Hash and save the new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            # Mark that the student has successfully changed it
            if hasattr(user, 'student_profile'):
                user.student_profile.has_changed_password = True
                user.student_profile.save()

            return Response({"message": "Password updated successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IsTeacherOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # Agar so'rov turi xavfsiz (ya'ni faqat o'qish - GET, HEAD, OPTIONS) bo'lsa, ruxsat!
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Aks holda (yozish, o'zgartirish, o'chirish bo'lsa), faqat o'qituvchilarga ruxsat!
        # hasattr() funksiyasi User modelida 'teacher' profili bor yoki yo'qligini tekshiradi.
        return hasattr(request.user, 'teacher')

# 1. Talabalar uchun ro'yxatdan o'tish (Sign Up) API'si
class StudentSignUpView(generics.CreateAPIView):
    serializer_class = RegisterStudentSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Student muvaffaqiyatli ro'yxatdan o'tdi!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. Assignment (Vazifalar) uchun CRUD API
class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Assignment.objects.all()
        elif hasattr(user, 'student_profile'):
            return Assignment.objects.filter(subject__in=user.student_profile.subjects.all())
        return Assignment.objects.none()

# 3. Task (Shaxsiy topshiriqlar) uchun CRUD API
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # To'g'ridan-to'g'ri tizimga kirgan User ni beramiz
        return Task.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        # Yaratishda ham faqat User ning o'zini saqlaymiz
        serializer.save(student=self.request.user)

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

class UpdateStudentSubjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        if not hasattr(user, 'student_profile'):
            return Response({"error": "Only students can update subjects."}, status=status.HTTP_403_FORBIDDEN)
            
        student = user.student_profile
        new_subject_ids = request.data.get('subject_ids', [])
        
        if len(new_subject_ids) > 6 or len(new_subject_ids) == 0:
            return Response({"error": "Must select between 1 and 6 subjects."}, status=status.HTTP_400_BAD_REQUEST)
            
        subjects = Subject.objects.filter(id__in=new_subject_ids)
        student.subjects.set(subjects)
        
        return Response({"message": "Subjects updated successfully!"}, status=status.HTTP_200_OK)

class QuizViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return Quiz.objects.all()
        elif hasattr(user, 'student_profile'):
            return Quiz.objects.filter(subject__in=user.student_profile.subjects.all())
        return Quiz.objects.none()

# ---------------------------------------------------------
# NEW PROFILE SETTINGS VIEW (Replaces UpdateStudentSubjectsView)
# ---------------------------------------------------------
class StudentProfileSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            student = Student.objects.get(pk=pk)
        except Student.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = StudentProfileSettingsSerializer(student)
        return Response(serializer.data)

    def patch(self, request, pk):
        try:
            student = Student.objects.get(pk=pk)
        except Student.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        # Basic security: Ensure the logged-in student is updating their own profile
        if not hasattr(request.user, 'student_profile') or request.user.student_profile.id != student.id:
            return Response({"error": "You do not have permission to edit this profile."}, status=status.HTTP_403_FORBIDDEN)

        # Handle updating subjects if they were provided in the request
        new_subject_ids = request.data.get('subject_ids')
        
        if new_subject_ids is not None:
            if len(new_subject_ids) > 6 or len(new_subject_ids) == 0:
                return Response({"error": "Must select between 1 and 6 subjects."}, status=status.HTTP_400_BAD_REQUEST)
            
            subjects = Subject.objects.filter(id__in=new_subject_ids)
            student.subjects.set(subjects)

        # Return the freshly updated profile data back to the frontend
        serializer = StudentProfileSettingsSerializer(student)
        return Response({
            "message": "Profile updated successfully!",
            "profile": serializer.data
        }, status=status.HTTP_200_OK)