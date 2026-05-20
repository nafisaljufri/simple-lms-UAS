from django.db import models
from django.contrib.auth.models import AbstractUser


# ======================
# USER MODEL
# ======================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


# ======================
# CATEGORY (HIERARCHY)
# ======================
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


# ======================
# COURSE
# ======================
class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        return self.select_related('instructor', 'category')


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='courses/', null=True, blank=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    objects = CourseQuerySet.as_manager()

    def __str__(self):
        return self.title


# ======================
# LESSON
# ======================
class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.IntegerField()
    file_attachment = models.FileField(upload_to='attachments/', null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


# ======================
# ENROLLMENT
# ======================
class EnrollmentQuerySet(models.QuerySet):
    def for_student_dashboard(self):
        return self.select_related('course').prefetch_related('course__lessons')


class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('student', 'course')


# ======================
# PROGRESS
# ======================
class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)