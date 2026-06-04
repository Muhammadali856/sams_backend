from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Subject, Assignment, Task, Student, Teacher, Quiz
from .serializers import AssignmentSerializer, TaskSerializer
from .serializers import StudentSerializer, RegisterStudentSerializer, SubjectSerializer, QuizSerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomLoginSerializer, ChangePasswordSerializer, StudentProfileSettingsSerializer
from rest_framework.decorators import action, api_view, permission_classes
from django.contrib.auth.models import User
from django.db import transaction
import random

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
            return Assignment.objects.filter(teacher=user.teacher)
        elif hasattr(user, 'student_profile'):
            return Assignment.objects.filter(subject__in=user.student_profile.subjects.all())
        return Assignment.objects.none()
    
    def perform_create(self, serializer):
        if hasattr(self.request.user, 'teacher'):
            serializer.save(teacher=self.request.user.teacher)
        else:
            serializer.save()

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

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        subject = self.get_object()
        user = request.user

        # 1. Check the enrollment key
        provided_key = request.data.get('enrollment_key', '')
        if provided_key != subject.enrollment_key:
            return Response({"error": "Invalid enrollment key."}, status=status.HTTP_400_BAD_REQUEST)

        student = user.student_profile

        # 2. Check the 6-subject limit (unless they are already enrolled)
        if student.subjects.count() >= 6 and not student.subjects.filter(id=subject.id).exists():
            return Response({"error": "You can only select a maximum of 6 subjects."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Success! Add the subject to the student
        student.subjects.add(subject)
        return Response({"message": f"Successfully enrolled in {subject.name}!"}, status=status.HTTP_200_OK)

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
            return Quiz.objects.filter(teacher=user.teacher)
        elif hasattr(user, 'student_profile'):
            return Quiz.objects.filter(subject__in=user.student_profile.subjects.all())
        return Quiz.objects.none()

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'teacher'):
            serializer.save(teacher=self.request.user.teacher)
        else:
            serializer.save()

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_staff_teacher(request):
    user = request.user

    # 1. SECURITY WALL: Check if the user is a teacher AND has the Head Teacher switch set to True
    if not hasattr(user, 'teacher') or not user.teacher.is_head_teacher:
        return Response(
            {"error": "Access Denied. Only Head Teachers can create new staff accounts."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # 2. Grab the data sent from React
    data = request.data
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    email = data.get('email', '')

    if not username or not password:
        return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "That Student ID / Username is already taken."}, status=status.HTTP_400_BAD_REQUEST)

    # 3. Securely create both records in the database
    try:
        with transaction.atomic():
            new_user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            # Link the new user to a teacher profile (defaulting to standard teacher)
            Teacher.objects.create(user=new_user, is_head_teacher=False)
            
        return Response({"message": f"Successfully created teacher account for {first_name} {last_name}!"}, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# STEP A: Request the 6-Digit Code
class RequestPasswordResetOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        student_id = request.data.get('student_id', '').strip().upper()
        
        try:
            user = User.objects.get(username=student_id)
            
            if not hasattr(user, 'student_profile'):
                return Response({"error": "This recovery portal is for student accounts only."}, status=status.HTTP_400_BAD_REQUEST)
            
            # STAGE 3 SECURITY CHECK: Ensure they have logged in normally at least once
            if not user.student_profile.has_changed_password:
                return Response({
                    "error": "Your account has not been activated yet. Please use the 'First time ?' button to complete your initial login."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate random 6-digit string
            otp_code = str(random.randint(100000, 999999))
            
            # Clean up any lingering old codes for this user
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(user=user, otp_code=otp_code)
            
            # Fire the email through Xiamen Outlook SMTP servers
            send_mail(
                subject="SAMS Password Reset Verification Code",
                message=f"Hello {user.first_name},\n\nYou requested a password reset code for SAMS.\n\nYour 6-digit verification code is: {otp_code}\n\nThis code will expire in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return Response({"message": "Verification code sent to your Outlook email."}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Standard cybersecurity mitigation: obfuscate response so attackers can't scrape valid IDs
            return Response({"message": "Verification code sent to your Outlook email."}, status=status.HTTP_200_OK)


# STEP B: Verify Only the 6-Digit Code (Unlocks the next screen on React)
class VerifyPasswordResetOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        student_id = request.data.get('student_id', '').strip().upper()
        otp_code = request.data.get('otp_code', '').strip()

        try:
            user = User.objects.get(username=student_id)
            otp_record = PasswordResetOTP.objects.filter(user=user, otp_code=otp_code).latest('created_at')

            if not otp_record.is_valid():
                return Response({"error": "This code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Code verified successfully."}, status=status.HTTP_200_OK)

        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return Response({"error": "Incorrect verification code."}, status=status.HTTP_400_BAD_REQUEST)


# STEP C: Finalize and Change Password
class ConfirmPasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        student_id = request.data.get('student_id', '').strip().upper()
        otp_code = request.data.get('otp_code', '').strip()
        new_password = request.data.get('new_password', '')

        if len(new_password) < 8:
            return Response({"error": "Your new password must be at least 8 characters long."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=student_id)
            otp_record = PasswordResetOTP.objects.filter(user=user, otp_code=otp_code).latest('created_at')

            if not otp_record.is_valid():
                return Response({"error": "Session expired. Please start over."}, status=status.HTTP_400_BAD_REQUEST)

            # Update, hash, and commit the new password to Neon DB
            user.set_password(new_password)
            user.save()
            
            # Clear the token out of database immediately after use
            otp_record.delete()

            return Response({"message": "Your password has been reset successfully!"}, status=status.HTTP_200_OK)

        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return Response({"error": "Session invalid. Please request a new code."}, status=status.HTTP_400_BAD_REQUEST)