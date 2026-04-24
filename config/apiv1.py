from ninja import NinjaAPI
from ninja import Schema
from lms.models import Enrollment, Course, Lesson, Progress
from .schemas import CourseIn, EnrollmentIn, ProgressIn, RegisterSchema, LoginSchema, UpdateProfileSchema, RefreshSchema
from .jwt_auth import JWTAuth
from django.contrib.auth import get_user_model
from .auth import create_access_token, create_refresh_token, decode_token
from django.shortcuts import get_object_or_404
from .permissions import is_instructor, is_admin

api = NinjaAPI()
api_auth = JWTAuth()
User = get_user_model()

# ======================
# RESPONSE HELPER
# ======================
def success_response(data=None, message="Success"):
    return {
        "status": "success",
        "message": message,
        "data": data
    }

def error_response(message="Error"):
    return {
        "status": "error",
        "message": message
    }

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
        return api.create_response(request, error_response("Username sudah ada"), status=400)
    user = User.objects.create_user(username=data.username, password=data.password, role=data.role)
    return api.create_response(request, success_response({"id": user.id}, "Register berhasil"), status=201)

@api.post("/auth/login")
def login(request, data: LoginSchema):
    user = User.objects.filter(username=data.username).first()
    if not user or not user.check_password(data.password):
        return api.create_response(request, error_response("Invalid credentials"), status=401)

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)  # tambahan

    return success_response(
        {"access_token": access, "refresh_token": refresh},  # tambahan
        "Login berhasil"
    )

@api.get("/auth/me", auth=api_auth)
def get_me(request):
    user = request.auth

    return success_response({
        "id": user.id,
        "username": user.username,
        "role": user.role
    }, "User data")

@api.post("/auth/refresh")
def refresh_token(request, data: RefreshSchema):
    payload = decode_token(data.refresh_token)
    if not payload:
        return api.create_response(request, error_response("Token tidak valid"), status=401)
    token = create_access_token(payload["user_id"])
    return success_response({"access_token": token}, "Token refreshed")

@api.put("/auth/me", auth=api_auth)
def update_profile(request, data: UpdateProfileSchema):
    user = request.auth
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
    courses = list(qs[(page-1)*limit : page*limit].values("id","title","description"))
    return success_response({"total": total, "page": page, "results": courses})

@api.get("/courses")
def list_courses(request):
    courses = [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description
        }
        for c in Course.objects.all()
    ]

    return success_response(courses, "List courses")

@api.get("/courses/{course_id}")
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)

    return success_response({
        "id": course.id,
        "title": course.title,
        "description": course.description
    }, "Detail course")

@api.post("/courses", auth=api_auth)
@is_instructor
def create_course(request, data: CourseIn):
    user = request.auth

    course = Course.objects.create(
        title=data.title,
        description=data.description,
        instructor=user
    )

    return api.create_response(
        request,
        success_response({"id": course.id}, "Course created"),
        status=201
    )

@api.patch("/courses/{course_id}", auth=api_auth)
def update_course(request, course_id: int, data: CourseIn):
    user = request.auth
    course = get_object_or_404(Course, id=course_id)

    if course.instructor != user:
        return api.create_response(
            request,
            error_response("Not your course"),
            status=403
        )

    course.title = data.title
    course.description = data.description
    course.save()

    return success_response(None, "Course updated")

@api.delete("/courses/{course_id}", auth=api_auth)
def delete_course(request, course_id: int):
    user = request.auth

    if user.role != "admin":
        return api.create_response(
            request,
            error_response("Only admin"),
            status=403
        )

    course = get_object_or_404(Course, id=course_id)
    course.delete()

    return success_response(None, "Course deleted")

# ======================
# ENROLLMENT
# ======================
@api.post("/enrollments", auth=api_auth)
def enroll(request, data: EnrollmentIn):
    user = request.auth

    if user.role != "student":
        return api.create_response(
            request,
            error_response("Only student"),
            status=403
        )

    course = get_object_or_404(Course, id=data.course_id)

    enrollment, created = Enrollment.objects.get_or_create(
        student=user,
        course=course
    )

    if not created:
        return api.create_response(
            request,
            error_response("Already enrolled"),
            status=400
        )

    return success_response(None, "Enrolled")

@api.get("/enrollments/my-courses", auth=api_auth)
def my_courses(request):
    user = request.auth

    enrollments = Enrollment.objects.filter(student=user)

    data = [
        {
            "id": e.id,
            "course_id": e.course.id,
            "title": e.course.title
        }
        for e in enrollments
    ]

    return success_response(data, "My courses")

# ======================
# PROGRESS
# ======================
@api.post("/progress", auth=api_auth)
def mark_progress(request, data: ProgressIn):
    user = request.auth

    lesson = get_object_or_404(Lesson, id=data.lesson_id)

    progress, _ = Progress.objects.get_or_create(
        student=user,
        lesson=lesson
    )

    progress.completed = True
    progress.save()

    return success_response(None, "Completed")