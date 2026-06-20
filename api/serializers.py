from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from .models import Subject, Teacher, Student, Assignment, Task, Quiz
from rest_framework import serializers

# 1. Custom Login Serializer
# 1. Custom Unified Login Serializer
class CustomLoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Prevent DRF from blocking the request when looking for the default 'username'
        self.fields['username'] = serializers.CharField(required=False)
        
        # Our custom unified fields
        self.fields['identifier'] = serializers.CharField(required=True)
        self.fields['full_name'] = serializers.CharField(required=False)

    def validate(self, attrs):
        identifier = attrs.get('identifier', '').strip()
        password = attrs.get('password')
        
        # 1. Find User by ID/Username (Case Insensitive)
        try:
            user = User.objects.get(username__iexact=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid ID or password."})

        # 2. Verify Password
        if not user.check_password(password):
            raise serializers.ValidationError({"detail": "Incorrect password."})
            
        # 3. Determine Role
        is_student = hasattr(user, 'student_profile')
        is_teacher = hasattr(user, 'teacher')

        if not is_student and not is_teacher:
            raise serializers.ValidationError({"detail": "This account has no valid role configured."})

        # 4. FIRST TIME LOGIN CHECK (Students Only)
        if is_student and not user.student_profile.has_changed_password:
            if 'full_name' not in attrs or not attrs['full_name'].strip():
                raise serializers.ValidationError({
                    "detail": "First time logging in? Please verify your Full Name.",
                    "first_time_required": True 
                })
            
            raw_full_name = attrs.get('full_name', '')
            submitted_name = " ".join(raw_full_name.split()).upper()
            raw_db_name = f"{user.first_name} {user.last_name}"
            db_name = " ".join(raw_db_name.split()).upper()

            if submitted_name != db_name:
                raise serializers.ValidationError({"detail": "Identity verification failed. Name does not match."})

        # 5. Generate Tokens
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'username': user.username,
        }

        # 6. Append Role-Specific Data
        if is_student:
            data['role'] = 'student'
            data['user_id'] = user.student_profile.id
            data['studentId'] = user.username 
            data['require_password_change'] = not user.student_profile.has_changed_password
        elif is_teacher:
            data['role'] = 'teacher'
            data['user_id'] = user.teacher.id
            data['require_password_change'] = False
            data['is_head_teacher'] = user.teacher.is_head_teacher

        return data

# 2. Password Change Serializer
class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, min_length=8)

# Foydalanuvchi ma'lumotlarini chiroyli formatda qaytarish uchun yordamchi serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

# Fanlar (subjects) uchun serializer
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'enrollment_key'] 
        
        extra_kwargs = {
            'enrollment_key': {'write_only': True} 
        }

# O'qituvchilar profilini to'liq ko'rsatish uchun serializer
class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True) 
    
    class Meta:
        model = Teacher
        fields = '__all__'

# Talabalar profilini ko'rsatish uchun serializer
class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    subject_names = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name',
        source='subjects'
    )
    
    class Meta:
        model = Student
        fields = ['id', 'user', 'subjects', 'subject_names', 'is_active']

# Talaba ro'yxatdan o'tayotganda
class RegisterStudentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    student_id = serializers.CharField(source='username') 

    class Meta:
        model = User
        fields = ['student_id', 'password', 'first_name', 'last_name', 'email', 'subject_ids']

    def validate_subject_ids(self, value):
        if len(value) > 6:
            raise serializers.ValidationError("A student can only choose up to 6 subjects.")
        if len(value) == 0:
            raise serializers.ValidationError("A student must choose at least 1 subject.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        subject_ids = validated_data.pop('subject_ids')
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        student = Student.objects.create(user=user)
        
        subjects = Subject.objects.filter(id__in=subject_ids)
        student.subjects.set(subjects)

        return user

# Vazifalar uchun serializer
class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'subject', 'name', 'description', 'deadline', 'created_at', 'teacher'] 
        read_only_fields = ['teacher', 'created_at']

# Shaxsiy tasklar uchun serializer
class TaskSerializer(serializers.ModelSerializer):
    # Student maydoni avtomatik to'ldirilishi va xavfsizlik uchun read_only qilinadi
    student = serializers.ReadOnlyField(source='student.username')

    class Meta:
        model = Task
        fields = ['id', 'student', 'name', 'description', 'status', 'created_at']

class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['id', 'subject', 'name', 'description', 'deadline', 'created_at', 'teacher']
        read_only_fields = ['teacher', 'created_at']

class StudentProfileSettingsSerializer(serializers.ModelSerializer):
    # Read-only fields pulled from the related User model
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    # Read-only list of subject names for display
    subject_names = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name', source='subjects'
    )
    
    # Write-only field for updating subjects
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Student
        fields = [
            'id', 
            'first_name', 
            'last_name', 
            'email', 
            'subjects', 
            'subject_names', 
            'has_changed_password', 
            'subject_ids'
        ]