from django.db import models
from django.contrib.auth.models import User

# 1. Subjects (Fanlar) jadvali
class Subject(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.name

# 2. Teacher (O'qituvchilar) jadvali
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

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
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name