from ninja import NinjaAPI, File, Query, Schema, Router
from ninja.files import UploadedFile
from ninja.pagination import paginate, PageNumberPagination
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from lms.models import Enrollment, Course, Lesson, Progress
from lms.tasks import test_task
from .schemas import (
    CourseIn, CourseUpdateSchema, CourseFilter,
    LessonIn, LessonOut, LessonUpdateSchema,
    EnrollmentIn, ProgressIn,
    RegisterSchema, UpdateProfileSchema
)
from typing import List, Optional
import redis

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# Inisialisasi main API dengan judul
api = NinjaAPI(title="Simple LMS API", version="1.0.0")
apiAuth = HttpJwtAuth()
User = get_user_model()

class CourseOut(Schema):
    id: int
    title: str
    description: str

# ======================
# RESPONSE HELPER
# ======================
def success_response(data=None, message="Success"):
    return {"status": "success", "message": message, "data": data}

def error_response(message="Error"):
    return {"status": "error", "message": message}

def is_admin_user(user):
    return user.role == "admin" or user.is_superuser

def can_manage_course(user, course):
    return is_admin_user(user) or course.instructor == user

# ======================
# 1. ROUTER: AUTH
# ======================
auth_router = Router(tags=["Authentication"])
api.add_router("/auth/", auth_router)
api.add_router("/auth/", mobile_auth_router)  # Untuk login/token dari ninja-simple-jwt

@auth_router.post("/register")
def register(request, data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah ada")
    user = User.objects.create_user(
        username=data.username,
        password=data.password,
        role=data.role
    )
    return api.create_response(request, success_response({"id": user.id}, "Register berhasil"), status=201)

@auth_router.get("/me", auth=apiAuth)
def get_me(request):
    user = User.objects.get(pk=request.user.id)
    return success_response({"id": user.id, "username": user.username, "role": user.role}, "User data")

@auth_router.put("/me", auth=apiAuth)
def update_profile(request, data: UpdateProfileSchema):
    user = User.objects.get(pk=request.user.id)
    user.username = data.username
    user.save()
    return success_response({"id": user.id, "username": user.username, "role": user.role}, "Profile updated")

# ======================
# 2. ROUTER: COURSES
# ======================
courses_router = Router(tags=["Courses"])
api.add_router("/courses", courses_router)

@courses_router.get("", response=List[CourseOut])
@paginate(PageNumberPagination, page_size=10)
def list_courses(request, filters: CourseFilter = Query(...), ordering: str = '-id'):
    q = request.GET.get('q')
    category = request.GET.get('category')
    instructor = request.GET.get('instructor')
    allowed_fields = [
        'title', '-title', 'id', '-id',
        'description', '-description',
        'category__name', '-category__name',
        'instructor__username', '-instructor__username',
    ]
    if ordering not in allowed_fields:
        ordering = '-id'
    qs = Course.objects.select_related('instructor', 'category').all()
    qs = filters.filter(qs)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q) |
            Q(instructor__username__icontains=q)
        )
    if category:
        if category.isdigit():
            qs = qs.filter(category_id=int(category))
        else:
            qs = qs.filter(category__name__icontains=category)
    if instructor:
        if instructor.isdigit():
            qs = qs.filter(instructor_id=int(instructor))
        else:
            qs = qs.filter(instructor__username__icontains=instructor)
    qs = qs.order_by(ordering)
    return qs

@courses_router.get("/popular")
def popular_courses(request):
    top = r.zrevrange('popular_courses', 0, 9, withscores=True)
    if not top:
        enrollments = Enrollment.objects.all()
        for e in enrollments:
            r.zincrby('popular_courses', 1, f'course:{e.course.id}')
        top = r.zrevrange('popular_courses', 0, 9, withscores=True)
    result = []
    for course_key, score in top:
        course_id = int(course_key.split(':')[1])
        try:
            course = Course.objects.get(id=course_id)
            result.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "enrollment_count": int(score)
            })
        except Course.DoesNotExist:
            pass
    return success_response(result, "Top 10 popular courses")

@courses_router.get("/{course_id}")
def course_detail(request, course_id: int):
    cache_key = f'course_detail:{course_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return success_response(cached, "Detail course (cached)")
    course = get_object_or_404(Course, id=course_id)
    data = {"id": course.id, "title": course.title, "description": course.description}
    cache.set(cache_key, data, timeout=300)
    return success_response(data, "Detail course")

@courses_router.post("", auth=apiAuth)
def create_course(request, data: CourseIn):
    user = User.objects.get(pk=request.user.id)
    if user.role != "instructor" and not is_admin_user(user):
        raise HttpError(403, "Instructor or admin only")
    course = Course.objects.create(
        title=data.title, description=data.description, instructor=user
    )
    cache.delete('courses_list')
    return api.create_response(request, success_response({"id": course.id}, "Course created"), status=201)

@courses_router.patch("/{course_id}", auth=apiAuth)
def update_course(request, course_id: int, data: CourseUpdateSchema):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if not can_manage_course(user, course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa mengedit")
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(course, attr, value)
    course.save()
    cache.delete('courses_list')
    cache.delete(f'course_detail:{course_id}')
    return success_response(None, "Course updated")

@courses_router.delete("/{course_id}", auth=apiAuth)
def delete_course(request, course_id: int):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if not can_manage_course(user, course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa menghapus")
    course.delete()
    cache.delete('courses_list')
    cache.delete(f'course_detail:{course_id}')
    return success_response(None, "Course deleted")

@courses_router.post("/{course_id}/upload-image", auth=apiAuth)
def upload_course_image(request, course_id: int, file: UploadedFile = File(...)):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if not can_manage_course(user, course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa upload image")
    if file.size > 2 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 2MB")
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HttpError(400, "Tipe file harus JPEG, PNG, atau WebP")
    course.image = file
    course.save()
    return success_response({"filename": file.name}, "Image berhasil diupload")

@courses_router.post("/{course_id}/visit")
def visit_course(request, course_id: int):
    visited = request.session.get('visited_courses', [])
    if course_id not in visited:
        visited.append(course_id)
        request.session['visited_courses'] = visited
    return success_response({
        "course_id": course_id,
        "total_visited": len(visited),
        "visited_courses": visited
    }, "Visit recorded")

# ======================
# 3. ROUTER: LESSONS
# ======================
lessons_router = Router(tags=["Lessons"])
api.add_router("/lessons", lessons_router)

@lessons_router.get("", response=List[LessonOut])
@paginate(PageNumberPagination, page_size=10)
def list_lessons(request, course_id: Optional[int] = None):
    qs = Lesson.objects.select_related('course').all()
    if course_id is not None:
        qs = qs.filter(course_id=course_id)
    return qs

@lessons_router.get("/{lesson_id}")
def lesson_detail(request, lesson_id: int):
    lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
    data = {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "content": lesson.content,
        "order": lesson.order,
    }
    return success_response(data, "Detail lesson")

@lessons_router.post("", auth=apiAuth)
def create_lesson(request, data: LessonIn):
    user = User.objects.get(pk=request.user.id)
    course = get_object_or_404(Course, id=data.course_id)
    if not can_manage_course(user, course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa membuat lesson")
    lesson = Lesson.objects.create(
        course=course,
        title=data.title,
        content=data.content,
        order=data.order,
    )
    cache.delete(f'course_detail:{course.id}')
    return api.create_response(request, success_response({"id": lesson.id}, "Lesson created"), status=201)

@lessons_router.patch("/{lesson_id}", auth=apiAuth)
def update_lesson(request, lesson_id: int, data: LessonUpdateSchema):
    user = User.objects.get(pk=request.user.id)
    lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
    if not can_manage_course(user, lesson.course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa mengedit lesson")
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(lesson, attr, value)
    lesson.save()
    cache.delete(f'course_detail:{lesson.course_id}')
    return success_response(None, "Lesson updated")

@lessons_router.delete("/{lesson_id}", auth=apiAuth)
def delete_lesson(request, lesson_id: int):
    user = User.objects.get(pk=request.user.id)
    lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
    course_id = lesson.course_id
    if not can_manage_course(user, lesson.course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa menghapus lesson")
    lesson.delete()
    cache.delete(f'course_detail:{course_id}')
    return success_response(None, "Lesson deleted")

@lessons_router.post("/{lesson_id}/upload-attachment", auth=apiAuth)
def upload_attachment(request, lesson_id: int, file: UploadedFile = File(...)):
    user = User.objects.get(pk=request.user.id)
    lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
    if not can_manage_course(user, lesson.course):
        raise HttpError(403, "Hanya admin atau pemilik course yang bisa upload attachment")
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

@lessons_router.get("/{lesson_id}/download", auth=apiAuth)
def download_attachment(request, lesson_id: int):
    user = User.objects.get(pk=request.user.id)
    lesson = get_object_or_404(Lesson.objects.select_related('course'), id=lesson_id)
    is_member = Enrollment.objects.filter(student=user, course=lesson.course).exists()
    if not is_member and not can_manage_course(user, lesson.course):
        raise HttpError(403, "Anda harus terdaftar di course ini untuk mendownload")
    if not lesson.file_attachment:
        raise HttpError(404, "Lesson ini tidak memiliki file attachment")
    return FileResponse(
        lesson.file_attachment.open(),
        as_attachment=True,
        filename=lesson.file_attachment.name.split('/')[-1]
    )

# ======================
# 4. ROUTER: ENROLLMENTS & PROGRESS
# ======================
enrollments_router = Router(tags=["Enrollments"])
api.add_router("/enrollments", enrollments_router)

@enrollments_router.post("", auth=apiAuth)
def enroll(request, data: EnrollmentIn):
    user = User.objects.get(pk=request.user.id)
    if user.role != "student":
        raise HttpError(403, "Only student")
    course = get_object_or_404(Course, id=data.course_id)
    enrollment, created = Enrollment.objects.get_or_create(student=user, course=course)
    if not created:
        raise HttpError(400, "Already enrolled")
    r.zincrby('popular_courses', 1, f'course:{data.course_id}')
    return success_response(None, "Enrolled")

@enrollments_router.get("/my-courses", auth=apiAuth)
def my_courses(request):
    user = User.objects.get(pk=request.user.id)
    enrollments = Enrollment.objects.filter(student=user).select_related('course')
    data = [{"id": e.id, "course_id": e.course.id, "title": e.course.title} for e in enrollments]
    return success_response(data, "My courses")

@enrollments_router.post("/{enrollment_id}/progress", auth=apiAuth)
def mark_progress(request, enrollment_id: int, data: ProgressIn):
    user = User.objects.get(pk=request.user.id)
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=user)
    lesson = get_object_or_404(Lesson, id=data.lesson_id)
    if lesson.course_id != enrollment.course_id:
        raise HttpError(400, "Lesson tidak termasuk dalam course enrollment ini")
    progress, _ = Progress.objects.get_or_create(student=user, lesson=lesson)
    progress.completed = True
    progress.save()
    return success_response(None, "Completed")

# ======================
# 5. ROUTER: DASHBOARD
# ======================
dashboard_router = Router(tags=["Dashboard"])
api.add_router("/dashboard", dashboard_router)

@dashboard_router.get("/student", auth=apiAuth)
def student_dashboard(request):
    user = User.objects.get(pk=request.user.id)
    if user.role != "student":
        raise HttpError(403, "Student only")

    enrollments = list(
        Enrollment.objects.filter(student=user)
        .select_related('course')
        .annotate(total_lessons=Count('course__lessons', distinct=True))
    )
    course_ids = [enrollment.course_id for enrollment in enrollments]
    completed_by_course = {
        item['lesson__course_id']: item['completed_count']
        for item in Progress.objects.filter(
            student=user,
            completed=True,
            lesson__course_id__in=course_ids,
        )
        .values('lesson__course_id')
        .annotate(completed_count=Count('lesson_id', distinct=True))
    }

    active_courses = 0
    completed_courses = 0
    progress_values = []
    course_summaries = []

    for enrollment in enrollments:
        total_lessons = enrollment.total_lessons
        completed_lessons = completed_by_course.get(enrollment.course_id, 0)
        progress_percent = round((completed_lessons / total_lessons) * 100, 2) if total_lessons else 0
        progress_values.append(progress_percent)
        if total_lessons and completed_lessons >= total_lessons:
            completed_courses += 1
        else:
            active_courses += 1
        course_summaries.append({
            "enrollment_id": enrollment.id,
            "course_id": enrollment.course_id,
            "title": enrollment.course.title,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "progress_percent": progress_percent,
        })

    recent_progress = (
        Progress.objects.filter(student=user, lesson__course_id__in=course_ids)
        .select_related('lesson', 'lesson__course')
        .order_by('-id')[:5]
    )
    recently_accessed_lessons = [
        {
            "lesson_id": progress.lesson_id,
            "lesson_title": progress.lesson.title,
            "course_id": progress.lesson.course_id,
            "course_title": progress.lesson.course.title,
            "completed": progress.completed,
        }
        for progress in recent_progress
    ]

    total_enrollments = len(enrollments)
    average_progress = round(sum(progress_values) / total_enrollments, 2) if total_enrollments else 0
    data = {
        "total_enrollments": total_enrollments,
        "active_courses": active_courses,
        "completed_courses": completed_courses,
        "average_progress": average_progress,
        "recently_accessed_lessons": recently_accessed_lessons,
        "summary": {
            "completed_lessons": sum(completed_by_course.values()),
            "total_lessons": sum(enrollment.total_lessons for enrollment in enrollments),
            "courses": course_summaries,
        },
    }
    return success_response(data, "Student dashboard")

@dashboard_router.get("/instructor", auth=apiAuth)
def instructor_dashboard(request):
    user = User.objects.get(pk=request.user.id)
    if user.role != "instructor" and not is_admin_user(user):
        raise HttpError(403, "Instructor or admin only")

    courses = Course.objects.all() if is_admin_user(user) else Course.objects.filter(instructor=user)
    courses = courses.select_related('instructor', 'category')
    course_ids = list(courses.values_list('id', flat=True))
    total_courses = len(course_ids)
    total_lessons = Lesson.objects.filter(course_id__in=course_ids).count()
    enrollments = Enrollment.objects.filter(course_id__in=course_ids)
    total_enrollments = enrollments.count()
    total_students = enrollments.values('student_id').distinct().count()

    possible_progress = (
        enrollments.annotate(lesson_count=Count('course__lessons'))
        .aggregate(total=Sum('lesson_count'))['total'] or 0
    )
    completed_progress = Progress.objects.filter(
        completed=True,
        lesson__course_id__in=course_ids,
        student__enrollment__course_id__in=course_ids,
    ).distinct().count()
    completion_rate = round((completed_progress / possible_progress) * 100, 2) if possible_progress else 0

    course_stats = [
        {
            "course_id": item['id'],
            "title": item['title'],
            "lesson_count": item['lesson_count'],
            "enrollment_count": item['enrollment_count'],
        }
        for item in courses.annotate(
            lesson_count=Count('lessons', distinct=True),
            enrollment_count=Count('enrollment', distinct=True),
        ).values('id', 'title', 'lesson_count', 'enrollment_count')
    ]

    data = {
        "total_courses": total_courses,
        "total_lessons": total_lessons,
        "total_students": total_students,
        "total_enrollments": total_enrollments,
        "completion_rate": completion_rate,
        "statistics": {
            "completed_progress": completed_progress,
            "possible_progress": possible_progress,
            "courses": course_stats,
        },
    }
    return success_response(data, "Instructor dashboard")

# ======================
# 6. ROUTER: GENERAL & HISTORY
# ======================
general_router = Router(tags=["General", "History"])
api.add_router("/", general_router)

@general_router.get("/hello")
def hello(request):
    return success_response(None, "API is running")

@general_router.post("/test-task", auth=apiAuth)
def trigger_test_task(request):
    user = User.objects.get(pk=request.user.id)
    if not is_admin_user(user):
        raise HttpError(403, "Admin only")
    # Jalankan task secara async
    result = test_task.delay()
    return success_response({"task_id": result.task_id}, "Task dikirim ke queue")

@general_router.get("/my-history")
def my_history(request):
    visited = request.session.get('visited_courses', [])
    return success_response({
        "total_visited": len(visited),
        "visited_courses": visited
    }, "Visit history")
