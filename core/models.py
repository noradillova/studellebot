from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=255)
    emoji = models.CharField(max_length=10, default="📚")
    def __str__(self):
        return self.name

class User(models.Model):
    telegram_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    streak = models.IntegerField(default=0)
    last_completed = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.username or self.telegram_id

class Task(models.Model):
    DIFFICULTY = [("easy","Easy"),("medium","Medium"),("hard","Hard")]
    title = models.CharField(max_length=255)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY, default="easy")
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.title
    @property
    def xp_reward(self):
        return {"easy":10,"medium":20,"hard":30}.get(self.difficulty,10)

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    question = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)
    def __str__(self):
        return self.question[:60]

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.user} — {self.text[:40]}"

class Message(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField()
    is_from_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.text[:40]}"