from django.contrib import admin
from .models import Course, Task, User, Quiz, Note, Message

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "emoji"]

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "difficulty", "is_active", "user"]
    list_filter = ["difficulty", "is_active", "course"]

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "first_name", "telegram_id", "level", "xp", "streak"]

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["question", "course", "answer"]
    list_filter = ["course"]

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["user", "text", "created_at"]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["user", "text", "is_from_user", "created_at"]