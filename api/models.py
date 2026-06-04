from django.db import models
from django.contrib.auth.models import User

# 1. Subjects (Fanlar) jadvali
class Subject(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    enrollment_key = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name

# 2. Teacher (O'qituvchilar) jadvali
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_head_teacher = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {'Head Teacher' if self.is_head_teacher else 'Teacher'}"

# 3. Student (Talabalar profili) jadvali
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    subjects = models.ManyToManyField(Subject, related_name='students')
    is_active = models.BooleanField(default=True)
    
    has_changed_password = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.user.username})"

# 4. Assignment (Vazifalar) jadvali
class Assignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# 5. Task (Shaxsiy topshiriqlar) jadvali
class Task(models.Model):
    STATUS_CHOICES = [
        ('not done', 'Not Done'),
        ('in process', 'In Process'),
        ('done', 'Done'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_tasks')
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_done')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

# 6 Quizzes (quizlar) jadvali
class Quiz(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        # The OTP code expires automatically after 10 minutes
        return self.created_at >= timezone.now() - timedelta(minutes=10)