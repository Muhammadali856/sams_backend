from django.contrib import admin
from .models import Programme, Teacher, Student, Assignment, Task, Quiz

@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_active')
    list_filter = ('is_active',)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'display_programmes', 'is_active')
    
    list_filter = ('programmes', 'is_active')
    search_fields = ('user__username', 'user__first_name')
    def display_programmes(self, obj):
        return ", ".join([p.name for p in obj.programmes.all()])
    display_programmes.short_description = 'Programmes'

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'programme', 'deadline')
    
    list_filter = ('programme',)
    
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
    list_display = ('id', 'name', 'programme')
    list_filter = ('programme',)
    search_fields = ('name',)