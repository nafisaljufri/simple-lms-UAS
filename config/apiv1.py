from ninja import NinjaAPI
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from lms.models import Enrollment, Course, Lesson, Progress
from .schemas import (
    CourseIn, EnrollmentIn, ProgressIn,
    RegisterSchema, UpdateProfileSchema
)

api = NinjaAPI()
apiAuth = HttpJwtAuth()
User = get_user_model()

# Register auth router dari ninja-simple-jwt
# Menyediakan: POST /auth/sign-in dan POST /auth/token-refresh
api.add_router("/auth/", mobile_auth_router)

# ======================
# RESPONSE HELPER
# ======================
def success_response(data=None, message="Success"):
    return {"status": "success", "message": message, "data": data}

def error_response(message="Error"):
    return {"status": "error", "message": message}

# ======================
# HELLO
# ======================
@api.get("/hello")
def hello(request):
    return success_response(None, "API is running")

# ======================
# AUTH
# ======================
@api.post("/auth/register")
def register(request, data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah ada")
    user = User.objects.create_user(
        username=data.username,
        password=data.password,
        role=data.role
    )
    return api.create_response(request, success_response({"id": user.id}, "Register berhasil"), status=201)

@api.get("/auth/me", auth=apiAuth)
def get_me(request):
    user = User.objects.get(pk=request.user.id)
    return success_response({
        "id": user.id,
        "username": user.username,
        "role": user.role
    }, "User data")

@api.put("/auth/me", auth=apiAuth)
def update_profile(request, data: UpdateProfileSchema):
    user = User.objects.get(pk=request.user.id)
    user.username = data.username
    user.save()
    return success_response({
        "id": user.id,
        "username": user.username,
        "role": user.role
    }, "Profile updated")

# ======================
# COURSES
# ======================
@api.get("/courses")
def list_courses(request, page: int = 1, limit: int = 10, search: str = ""):
    qs = Course.objects.all()
    if search:
        qs = qs.filter(title__icontains=search)
    total = qs.count()
    courses = list(qs[(page-1)*limit : page*limit].values("id", "title", "description"))
    return success_response({"total": total, "page": page, "results": courses})

@api.get("/courses/{course_id}")
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    return success_response({
        "id": course.id,
        "title": course.title,
        "description": course.description
    }, "Detail course")

@api.post("/courses", auth=apiAuth)
def create_course(request, data: CourseIn):
    user = User.objects.get(pk=request.user.id)
    if user.role != "instructor":
        raise HttpError(403, "Instructor only")
    course = Course.objects.create(
        title=data.title,
        description=data.description,
        instructor=user
    )
    return api.create_response(request, success_response({"id": course.id}, "Course created"), status=201)

@api.patch("/courses/{course_id}", auth=apiAuth)
def update_course(request, course_id: int, data: CourseIn):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != user:
        raise HttpError(403, "Hanya pemilik course yang bisa mengedit")
    course.title = data.title
    course.description = data.description
    course.save()
    return success_response(None, "Course updated")

@api.delete("/courses/{course_id}", auth=apiAuth)
def delete_course(request, course_id: int):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != user and not user.is_superuser:
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa menghapus")
    course.delete()
    return success_response(None, "Course deleted")

# ======================
# ENROLLMENT
# ======================
@api.post("/enrollments", auth=apiAuth)
def enroll(request, data: EnrollmentIn):
    user = User.objects.get(pk=request.user.id)
    if user.role != "student":
        raise HttpError(403, "Only student")
    course = get_object_or_404(Course, id=data.course_id)
    enrollment, created = Enrollment.objects.get_or_create(student=user, course=course)
    if not created:
        raise HttpError(400, "Already enrolled")
    return success_response(None, "Enrolled")

@api.get("/enrollments/my-courses", auth=apiAuth)
def my_courses(request):
    user = User.objects.get(pk=request.user.id)
    enrollments = Enrollment.objects.filter(student=user).select_related('course')
    data = [{"id": e.id, "course_id": e.course.id, "title": e.course.title} for e in enrollments]
    return success_response(data, "My courses")

# ======================
# PROGRESS
# ======================
@api.post("/enrollments/{enrollment_id}/progress", auth=apiAuth)
def mark_progress(request, enrollment_id: int, data: ProgressIn):
    user = User.objects.get(pk=request.user.id)
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=user)
    lesson = get_object_or_404(Lesson, id=data.lesson_id)
    progress, _ = Progress.objects.get_or_create(student=user, lesson=lesson)
    progress.completed = True
    progress.save()
    return success_response(None, "Completed")