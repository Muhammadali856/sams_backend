from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from .models import Programme, Teacher, Student, Assignment, Task, Quiz


# 1. Custom Login Serializer
class CustomLoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove default username and add our 3 fields
        self.fields['username'] = None 
        self.fields['student_id'] = serializers.CharField()
        self.fields['full_name'] = serializers.CharField()
        self.fields['password'] = serializers.CharField()

    def validate(self, attrs):
        student_id = attrs.get('student_id', '').strip().upper()
        password = attrs.get('password')
        
        # 1. Get the submitted full name, make it UPPERCASE, and remove extra spaces
        raw_full_name = attrs.get('full_name', '')
        submitted_name = " ".join(raw_full_name.split()).upper()

        # 2. Find user by Student ID
        try:
            user = User.objects.get(username=student_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid Student ID or Full Name."})

        # 3. Glue the database First Name and Last Name together and make it UPPERCASE
        raw_db_name = f"{user.first_name} {user.last_name}"
        db_name = " ".join(raw_db_name.split()).upper()

        # 4. Compare the two names
        if submitted_name != db_name:
            raise serializers.ValidationError({"detail": "Invalid Student ID or Full Name."})

        # 5. Check Password
        if not user.check_password(password):
            raise serializers.ValidationError({"detail": "Incorrect password."})

        # 6. Generate the JWT tokens
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        # 7. Tell the frontend if the user MUST change their password
        if hasattr(user, 'student_profile'):
            data['role'] = 'student'
            data['require_password_change'] = not user.student_profile.has_changed_password
        elif hasattr(user, 'teacher'):
            data['role'] = 'teacher'
            data['require_password_change'] = False

        return data

# 2. Password Change Serializer
class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, min_length=8)

# Foydalanuvchi ma'lumotlarini chiroyli formatda qaytarish uchun yordamchi serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

# Dasturlar (Yo'nalishlar) uchun serializer
class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
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
    
    # This magic line grabs the 'name' of EVERY programme the student is in
    programme_names = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name',
        source='programmes'
    )
    
    class Meta:
        model = Student
        # We use 'programmes' (plural) to match the new model field name
        fields = ['id', 'user', 'programmes', 'programme_names', 'is_active']

# Talaba ro'yxatdan o'tayotganda ham User, ham Student profilini birga yaratish uchun
class RegisterStudentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # Changed to ListField to accept an array like [1, 2, 4]
    programme_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True
    )
    student_id = serializers.CharField(source='username') 

    class Meta:
        model = User
        fields = ['student_id', 'password', 'first_name', 'last_name', 'email', 'programme_ids']

    # This built-in method automatically validates the programme_ids array
    def validate_programme_ids(self, value):
        if len(value) > 6:
            raise serializers.ValidationError("A student can only choose up to 6 programmes.")
        if len(value) == 0:
            raise serializers.ValidationError("A student must choose at least 1 programme.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        programme_ids = validated_data.pop('programme_ids')
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # Create the student profile first
        student = Student.objects.create(user=user)
        
        # Fetch the selected programmes from the database and link them to the student
        programmes = Programme.objects.filter(id__in=programme_ids)
        student.programmes.set(programmes)

        return user
# Vazifalar uchun serializer
class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        # student va status ni bu yerdan butunlay olib tashlaymiz:
        fields = ['id', 'programme', 'name', 'description', 'deadline', 'created_at'] 

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
        fields = ['id', 'programme', 'name', 'description', 'deadline', 'created_at']