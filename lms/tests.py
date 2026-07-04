import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from config.apiv1 import apiAuth
from lms.models import Course, Enrollment, Lesson, Progress


User = get_user_model()


class LMSAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username="admin1",
            password="password123",
            role="admin",
        )
        self.instructor = User.objects.create_user(
            username="instructor1",
            password="password123",
            role="instructor",
        )
        self.other_instructor = User.objects.create_user(
            username="instructor2",
            password="password123",
            role="instructor",
        )
        self.student = User.objects.create_user(
            username="student1",
            password="password123",
            role="student",
        )
        self.course = Course.objects.create(
            title="Django Ninja",
            description="Backend API course",
            instructor=self.instructor,
        )
        self.other_course = Course.objects.create(
            title="PostgreSQL",
            description="Database course",
            instructor=self.other_instructor,
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Intro",
            content="Intro content",
            order=1,
        )
        self.other_lesson = Lesson.objects.create(
            course=self.other_course,
            title="Database Intro",
            content="Database content",
            order=1,
        )

    def auth_as(self, user):
        def authenticate(request, token):
            request.user = user
            return user

        return patch.object(apiAuth, "authenticate", side_effect=authenticate)

    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

    def patch_json(self, path, payload):
        return self.client.patch(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

    def delete_auth(self, path):
        return self.client.delete(path, HTTP_AUTHORIZATION="Bearer test-token")

    def test_anonymous_can_only_access_public_read_endpoints(self):
        self.assertEqual(self.client.get("/api/courses").status_code, 200)
        self.assertEqual(self.client.get("/api/lessons").status_code, 200)
        self.assertEqual(self.client.get(f"/api/lessons/{self.lesson.id}").status_code, 200)

        protected_response = self.client.post(
            "/api/lessons",
            data=json.dumps({
                "course_id": self.course.id,
                "title": "Protected",
                "content": "Protected content",
                "order": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(protected_response.status_code, 401)

    def test_instructor_can_manage_only_owned_lessons(self):
        with self.auth_as(self.instructor):
            create_response = self.post_json(
                "/api/lessons",
                {
                    "course_id": self.course.id,
                    "title": "Owned Lesson",
                    "content": "Owned content",
                    "order": 2,
                },
            )
        self.assertEqual(create_response.status_code, 201)
        lesson_id = create_response.json()["data"]["id"]

        with self.auth_as(self.instructor):
            update_response = self.patch_json(
                f"/api/lessons/{lesson_id}",
                {"title": "Owned Lesson Updated"},
            )
        self.assertEqual(update_response.status_code, 200)

        with self.auth_as(self.instructor):
            forbidden_response = self.patch_json(
                f"/api/lessons/{self.other_lesson.id}",
                {"title": "Should fail"},
            )
        self.assertEqual(forbidden_response.status_code, 403)

        with self.auth_as(self.instructor):
            delete_response = self.delete_auth(f"/api/lessons/{lesson_id}")
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Lesson.objects.filter(id=lesson_id).exists())

    def test_student_cannot_modify_instructor_resources(self):
        with self.auth_as(self.student):
            course_response = self.patch_json(
                f"/api/courses/{self.course.id}",
                {"title": "Student edit"},
            )
        self.assertEqual(course_response.status_code, 403)

        with self.auth_as(self.student):
            lesson_response = self.post_json(
                "/api/lessons",
                {
                    "course_id": self.course.id,
                    "title": "Student lesson",
                    "content": "Should fail",
                    "order": 3,
                },
            )
        self.assertEqual(lesson_response.status_code, 403)

    def test_admin_has_full_course_and_lesson_access(self):
        with self.auth_as(self.admin):
            course_response = self.patch_json(
                f"/api/courses/{self.course.id}",
                {"title": "Admin updated course"},
            )
        self.assertEqual(course_response.status_code, 200)

        with self.auth_as(self.admin):
            lesson_response = self.post_json(
                "/api/lessons",
                {
                    "course_id": self.course.id,
                    "title": "Admin lesson",
                    "content": "Admin content",
                    "order": 3,
                },
            )
        self.assertEqual(lesson_response.status_code, 201)

        lesson_id = lesson_response.json()["data"]["id"]
        with self.auth_as(self.admin):
            delete_response = self.delete_auth(f"/api/lessons/{lesson_id}")
        self.assertEqual(delete_response.status_code, 200)

    def test_student_can_enroll_and_mark_valid_progress(self):
        with self.auth_as(self.student):
            enroll_response = self.post_json(
                "/api/enrollments",
                {"course_id": self.course.id},
            )
        self.assertEqual(enroll_response.status_code, 200)

        enrollment = Enrollment.objects.get(student=self.student, course=self.course)

        with self.auth_as(self.student):
            my_courses_response = self.client.get(
                "/api/enrollments/my-courses",
                HTTP_AUTHORIZATION="Bearer test-token",
            )
        self.assertEqual(my_courses_response.status_code, 200)

        with self.auth_as(self.student):
            progress_response = self.post_json(
                f"/api/enrollments/{enrollment.id}/progress",
                {"lesson_id": self.lesson.id},
            )
        self.assertEqual(progress_response.status_code, 200)
        self.assertTrue(
            Progress.objects.filter(
                student=self.student,
                lesson=self.lesson,
                completed=True,
            ).exists()
        )

    def test_progress_rejects_lesson_from_another_course(self):
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
        )

        with self.auth_as(self.student):
            progress_response = self.post_json(
                f"/api/enrollments/{enrollment.id}/progress",
                {"lesson_id": self.other_lesson.id},
            )
        self.assertEqual(progress_response.status_code, 400)
        self.assertFalse(
            Progress.objects.filter(
                student=self.student,
                lesson=self.other_lesson,
            ).exists()
        )
