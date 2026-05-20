from ninja import Schema, FilterSchema, Field
from typing import List
from typing import Optional
from pydantic import validator
from django.db.models import Q

# ======================
# USER
# ======================
class UserOut(Schema):
    id: int
    username: str
    role: str

class UpdateProfileSchema(Schema):
    username: str

# ======================
# AUTH
# ======================
class LoginSchema(Schema):
    username: str
    password: str

    @validator("username")
    def username_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Username tidak boleh kosong")
        return v

    @validator("password")
    def password_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Password tidak boleh kosong")
        return v

class RegisterSchema(Schema):
    username: str
    password: str
    role: str

class RefreshSchema(Schema):
    refresh_token: str

# ======================
# COURSE
# ======================
class CourseIn(Schema):
    title: str
    description: str

    @validator("title")
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Title tidak boleh kosong")
        return v

    @validator("description")
    def desc_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Description tidak boleh kosong")
        return v


class CourseOut(Schema):
    id: int
    title: str
    description: str
    instructor: UserOut


# ======================
# LESSON
# ======================
class LessonOut(Schema):
    id: int
    title: str


class DetailCourseOut(CourseOut):
    lessons: List[LessonOut]


# ======================
# ENROLLMENT
# ======================
class EnrollmentIn(Schema):
    course_id: int

    @validator("course_id")
    def course_id_valid(cls, v):
        if v <= 0:
            raise ValueError("Course ID tidak valid")
        return v


class EnrollmentOut(Schema):
    id: int
    course_id: int
    course_title: str


# ======================
# PROGRESS
# ======================
class ProgressIn(Schema):
    lesson_id: int

    @validator("lesson_id")
    def lesson_id_valid(cls, v):
        if v <= 0:
            raise ValueError("Lesson ID tidak valid")
        return v
    
class CourseUpdateSchema(Schema):
    title: Optional[str] = None
    description: Optional[str] = None

class CourseFilter(FilterSchema):
    search: Optional[str] = Field(
        None,
        q=['title__icontains', 'description__icontains']
    )

    def filter_search(self, value: str) -> Q:
        if value:
            return Q(title__icontains=value) | Q(description__icontains=value)
        return Q()