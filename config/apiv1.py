from ninja import NinjaAPI, File, Query, Schema
from ninja.files import UploadedFile
from ninja.pagination import paginate, PageNumberPagination
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from lms.models import Enrollment, Course, Lesson, Progress
from .schemas import (
    CourseIn, CourseUpdateSchema, CourseFilter,
    EnrollmentIn, ProgressIn,
    RegisterSchema, UpdateProfileSchema
)
from typing import List

api = NinjaAPI()
apiAuth = HttpJwtAuth()
User = get_user_model()

class CourseOut(Schema):
    id: int
    title: str
    description: str

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
    return success_response({"id": user.id, "username": user.username, "role": user.role}, "User data")

@api.put("/auth/me", auth=apiAuth)
def update_profile(request, data: UpdateProfileSchema):
    user = User.objects.get(pk=request.user.id)
    user.username = data.username
    user.save()
    return success_response({"id": user.id, "username": user.username, "role": user.role}, "Profile updated")

# ======================
# COURSES
# ======================

@api.get("/courses", response=List[CourseOut])
@paginate(PageNumberPagination, page_size=10)
def list_courses(request, filters: CourseFilter = Query(...), ordering: str = '-id'):
    allowed_fields = ['title', '-title', 'id', '-id', 'description', '-description']
    if ordering not in allowed_fields:
        ordering = '-id'
    qs = Course.objects.all()
    qs = filters.filter(qs)
    qs = qs.order_by(ordering)
    return qs

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
def update_course(request, course_id: int, data: CourseUpdateSchema):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != user:
        raise HttpError(403, "Hanya pemilik course yang bisa mengedit")
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(course, attr, value)
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

@api.post("/courses/{course_id}/upload-image", auth=apiAuth)
def upload_course_image(request, course_id: int, file: UploadedFile = File(...)):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != user:
        raise HttpError(403, "Hanya pemilik course yang bisa upload image")
    if file.size > 2 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 2MB")
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HttpError(400, "Tipe file harus JPEG, PNG, atau WebP")
    course.image = file
    course.save()
    return success_response({"filename": file.name}, "Image berhasil diupload")

# ======================
# LESSONS (upload & download)
# ======================
@api.post("/lessons/{lesson_id}/upload-attachment", auth=apiAuth)
def upload_attachment(request, lesson_id: int, file: UploadedFile = File(...)):
    user = User.objects.get(pk=request.user.id)
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if lesson.course.instructor != user:
        raise HttpError(403, "Hanya pemilik course yang bisa upload attachment")
    if file.size > 10 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 10MB")
    allowed_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/zip'
    ]
    if file.content_type not in allowed_types:
        raise HttpError(400, "Tipe file harus PDF, DOCX, PPTX, atau ZIP")
    lesson.file_attachment = file
    lesson.save()
    return success_response({"filename": file.name}, "Attachment berhasil diupload")

@api.get("/lessons/{lesson_id}/download", auth=apiAuth)
def download_attachment(request, lesson_id: int):
    user = User.objects.get(pk=request.user.id)
    lesson = get_object_or_404(Lesson, id=lesson_id)
    is_member = Enrollment.objects.filter(student=user, course=lesson.course).exists()
    if not is_member:
        raise HttpError(403, "Anda harus terdaftar di course ini untuk mendownload")
    if not lesson.file_attachment:
        raise HttpError(404, "Lesson ini tidak memiliki file attachment")
    return FileResponse(
        lesson.file_attachment.open(),
        as_attachment=True,
        filename=lesson.file_attachment.name.split('/')[-1]
    )

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