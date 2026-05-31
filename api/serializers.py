from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from .models import Subject, Teacher, Student, Assignment, Task, Quiz
from rest_framework import serializers

class CustomLoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Make all identity fields optional so DRF doesn't block the request early
        self.fields['username'] = serializers.CharField(required=False)
        self.fields['student_id'] = serializers.CharField(required=False)
        self.fields['full_name'] = serializers.CharField(required=False)
        # Password remains required by default from the parent class

    def validate(self, attrs):
        password = attrs.get('password')
        
        # ==========================================
        # FLOW 1: TEACHER LOGIN (uses username)
        # ==========================================
        if 'username' in attrs and attrs['username'].strip():
            username = attrs.get('username')
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError({"detail": "Invalid username or password."})
            
            # Check password
            if not user.check_password(password):
                raise serializers.ValidationError({"detail": "Incorrect password."})
                
            # Ensure this is actually a teacher
            if not hasattr(user, 'teacher'):
                raise serializers.ValidationError({"detail": "This account is not a teacher account."})

       # ==========================================
        # FLOW 2 & 3: STUDENT LOGIN
        # ==========================================
        elif 'student_id' in attrs:
            student_id = attrs.get('student_id', '').strip().upper()

            # 1. Find user by Student ID
            try:
                user = User.objects.get(username=student_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({"detail": "Invalid Student ID or password."})

            # 2. Check Password
            if not user.check_password(password):
                raise serializers.ValidationError({"detail": "Incorrect password."})
                
            # 3. Ensure this is actually a student
            if not hasattr(user, 'student_profile'):
                raise serializers.ValidationError({"detail": "This account is not a student account."})

            # 4. FIRST TIME LOGIN CHECK: Only require Full Name if they haven't changed the default password
            if not user.student_profile.has_changed_password:
                if 'full_name' not in attrs or not attrs['full_name'].strip():
                    raise serializers.ValidationError({
                        "detail": "This is your first time logging in. Please click 'First time?' to verify your full name.",
                        "first_time_required": True 
                    })
                
                # Verify the provided Full Name matches the database
                raw_full_name = attrs.get('full_name', '')
                submitted_name = " ".join(raw_full_name.split()).upper()
                raw_db_name = f"{user.first_name} {user.last_name}"
                db_name = " ".join(raw_db_name.split()).upper()

                if submitted_name != db_name:
                    raise serializers.ValidationError({"detail": "Invalid Student ID or Full Name."})


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
        fields = '__all__'

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
        fields = ['id', 'subject', 'name', 'description', 'deadline', 'created_at'] 

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
        fields = ['id', 'subject', 'name', 'description', 'deadline', 'created_at']

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