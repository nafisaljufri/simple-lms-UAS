# Simple LMS - Django Ninja API

Simple LMS adalah backend Learning Management System sederhana yang dibangun dengan Django, Django Ninja, PostgreSQL, JWT Authentication, RBAC, Redis, dan Docker Compose.

Project ini menyediakan API untuk autentikasi, course, lesson, enrollment, progress belajar, upload file, cache Redis, session history, dan Celery task demo.

## Technology Stack

- Python 3.11
- Django
- Django Ninja
- PostgreSQL
- ninja-simple-jwt
- Redis
- Celery, RabbitMQ, Flower
- Docker Compose

## Docker Setup

Pastikan Docker Desktop sudah berjalan, lalu jalankan:

```bash
docker compose up -d
```

Service utama:

| Service | Port | Keterangan |
|---|---:|---|
| `web` | `8000` | Django API |
| `db` | `5432` | PostgreSQL |
| `redis` | `6379` | Cache, session, leaderboard |
| `rabbitmq` | `5672`, `15672` | Celery broker dan dashboard |
| `celery_worker` | - | Worker async task |
| `flower` | `5555` | Celery monitoring |

## Environment Variables

Buat file `.env` dari `.env.example`.

```bash
cp .env.example .env
```

Contoh konfigurasi:

```env
DEBUG=True
DB_NAME=lms_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

Jangan commit `.env` karena berisi konfigurasi lokal.

## Migration Steps

Jalankan migration setelah container aktif:

```bash
docker compose exec web python manage.py migrate
```

Opsional, buat superuser untuk akses Django Admin:

```bash
docker compose exec web python manage.py createsuperuser
```

API tersedia di:

```text
http://localhost:8000/api/
```

Swagger tersedia di:

```text
http://localhost:8000/api/docs
```

## Demo Accounts

Demo accounts dapat dibuat melalui Swagger atau Postman memakai endpoint `POST /api/auth/register`.

Gunakan data berikut untuk skenario demo:

| Role | Username | Password | Catatan |
|---|---|---|---|
| Admin | `admin1` | `password123` | Full access ke resource API |
| Instructor | `instructor1` | `password123` | Kelola course dan lesson miliknya |
| Student | `student1` | `password123` | Enroll course dan update progress |

Contoh register:

```json
{
  "username": "student1",
  "password": "password123",
  "role": "student"
}
```

## Authentication

Login menggunakan:

```text
POST /api/auth/sign-in
```

Body:

```json
{
  "username": "student1",
  "password": "password123"
}
```

Gunakan access token pada endpoint protected:

```text
Authorization: Bearer <access_token>
```

## Endpoint Summary

### Authentication

| Method | Endpoint | Auth | Keterangan |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Register user |
| POST | `/api/auth/sign-in` | Public | Login dan ambil JWT |
| POST | `/api/auth/token-refresh` | Public | Refresh access token |
| GET | `/api/auth/me` | JWT | Profil user login |
| PUT | `/api/auth/me` | JWT | Update username |

### Courses

| Method | Endpoint | Auth / Role | Keterangan |
|---|---|---|---|
| GET | `/api/courses` | Public | List course dengan pagination, search, ordering |
| GET | `/api/courses/popular` | Public | Top 10 popular courses dari Redis |
| GET | `/api/courses/{course_id}` | Public | Detail course |
| POST | `/api/courses` | Admin / Instructor | Buat course |
| PATCH | `/api/courses/{course_id}` | Admin / Owner | Update course |
| DELETE | `/api/courses/{course_id}` | Admin / Owner | Delete course |
| POST | `/api/courses/{course_id}/upload-image` | Admin / Owner | Upload image course |
| POST | `/api/courses/{course_id}/visit` | Public | Simpan visit history di session |

### Lessons

| Method | Endpoint | Auth / Role | Keterangan |
|---|---|---|---|
| GET | `/api/lessons` | Public | List lesson, optional `course_id` |
| GET | `/api/lessons/{lesson_id}` | Public | Detail lesson |
| POST | `/api/lessons` | Admin / Course Owner | Buat lesson |
| PATCH | `/api/lessons/{lesson_id}` | Admin / Course Owner | Update lesson |
| DELETE | `/api/lessons/{lesson_id}` | Admin / Course Owner | Delete lesson |
| POST | `/api/lessons/{lesson_id}/upload-attachment` | Admin / Course Owner | Upload attachment |
| GET | `/api/lessons/{lesson_id}/download` | Admin / Course Owner / Enrolled Student | Download attachment |

### Enrollments and Progress

| Method | Endpoint | Auth / Role | Keterangan |
|---|---|---|---|
| POST | `/api/enrollments` | Student | Enroll ke course |
| GET | `/api/enrollments/my-courses` | JWT | List course yang diikuti user |
| POST | `/api/enrollments/{enrollment_id}/progress` | Student pemilik enrollment | Tandai lesson selesai |

### General

| Method | Endpoint | Auth / Role | Keterangan |
|---|---|---|---|
| GET | `/api/hello` | Public | API health message sederhana |
| GET | `/api/my-history` | Public session | Riwayat visit course |
| POST | `/api/test-task` | Admin | Kirim Celery test task |

## RBAC Summary

| Role | Hak Akses |
|---|---|
| Anonymous | Endpoint public saja |
| Student | Lihat course/lesson, enroll, lihat course sendiri, update progress untuk lesson pada course yang di-enroll |
| Instructor | Buat course, kelola course/lesson miliknya, upload file untuk resource miliknya |
| Admin | Full access ke resource course/lesson dan task admin |

## How To Test With Swagger

1. Buka `http://localhost:8000/api/docs`.
2. Register user demo melalui `POST /api/auth/register`.
3. Login melalui `POST /api/auth/sign-in`.
4. Copy `access` token dari response.
5. Klik tombol authorize di Swagger.
6. Masukkan token dengan format:

```text
Bearer <access_token>
```

7. Jalankan skenario:
   - Instructor membuat course.
   - Instructor membuat lesson pada course.
   - Student enroll ke course.
   - Student update progress lesson pada enrollment tersebut.

## How To Test With Postman

1. Import collection:

```text
postman/simple-lms-advanced.postman_collection.json
```

2. Jalankan request register/login untuk role demo.
3. Simpan access token dari login.
4. Isi header Authorization pada request protected:

```text
Bearer <access_token>
```

5. Jalankan urutan berikut:
   - Register/login instructor.
   - Create course.
   - Create lesson.
   - Register/login student.
   - Enroll course.
   - Mark lesson progress.

## Automated Tests

Focused backend tests tersedia di `lms/tests.py`.

Jalankan dengan:

```bash
docker compose exec web python manage.py test lms
```

Coverage utama:

- RBAC course dan lesson
- Lesson CRUD
- Enrollment
- Progress validation antar course

## Screenshots

Beberapa screenshot pendukung tersedia di folder `img/`.

- Docker Compose: `img/docker-compose.png`
- Swagger: `img/swagger.png`
- Redis: `img/redis-ping.png`, `img/redis-monitor.png`, `img/redis-keys.png`
- Popular courses: `img/popular-courses.png`
- Query optimization: `img/query.png`

## Author

Nafis Aljufri
