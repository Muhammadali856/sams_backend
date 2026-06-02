from django.contrib import admin
from .models import Subject, Teacher, Student, Assignment, Task, Quiz

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_head_teacher')
    list_editable = ('is_head_teacher',)
    list_filter = ("is_active",)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'display_subjects', 'is_active')
    
    list_filter = ('subjects', 'is_active')
    search_fields = ('user__username', 'user__first_name')
    def display_subjects(self, obj):
        return ", ".join([s.name for s in obj.subjects.all()])
    display_subjects.short_description = 'Subjects'

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'subject', 'deadline')

    list_filter = ('subject',)

    search_fields = ('name',)
    ordering = ('-created_at',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'student', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'student__username')
    ordering = ('-created_at',)

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'subject')
    list_filter = ('subject',)
    search_fields = ('name',)