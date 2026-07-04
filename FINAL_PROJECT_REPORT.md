# Final Project Report - Simple LMS API

## Project Description

Simple LMS adalah backend Learning Management System sederhana berbasis REST API. Project ini dibuat menggunakan Django Ninja, PostgreSQL, JWT Authentication, Docker Compose, dan Role-Based Access Control.

Sistem menyediakan fitur utama untuk mengelola course, lesson, enrollment, dan progress belajar. Selain fitur wajib, project juga memiliki Redis caching, upload file, popular course leaderboard, session-based visit history, Celery worker, RabbitMQ, dan Flower monitoring.

## Implemented Mandatory Features

| Requirement | Status | Implementation |
|---|---|---|
| Docker Compose | Implemented | `docker-compose.yml` menjalankan web, PostgreSQL, Redis, RabbitMQ, Celery worker, dan Flower |
| PostgreSQL | Implemented | Django menggunakan engine `django.db.backends.postgresql` |
| JWT Authentication | Implemented | Login dan refresh token melalui `ninja-simple-jwt` |
| Swagger | Implemented | Swagger UI tersedia di `/api/docs` |
| RBAC | Implemented | Admin full access, instructor hanya resource miliknya, student akses enrollment/progress, anonymous public endpoint |
| Course CRUD | Implemented | Create, read, update, delete course |
| Lesson CRUD | Implemented | Create, read, update, delete lesson |
| Enrollment | Implemented | Student dapat enroll course dan melihat course miliknya |
| Progress | Implemented | Student dapat menandai lesson selesai hanya pada course yang di-enroll |
| README | Implemented | Dokumentasi setup, endpoint, Swagger, Postman, dan testing |

## Implemented Additional Features

- Course search, ordering, and pagination.
- Course image upload.
- Lesson attachment upload and download.
- Redis cache-aside untuk course detail.
- Redis sorted set untuk popular courses.
- Redis-backed session history.
- Celery test task.
- RabbitMQ broker.
- Flower monitoring dashboard.
- Django Admin registration.
- Category hierarchy model.

## Architecture Summary

Project mengikuti struktur Django standar dengan satu aplikasi utama `lms` dan konfigurasi API di module `config`.

Komponen utama:

| Layer | File / Folder | Keterangan |
|---|---|---|
| Models | `lms/models.py` | User, Category, Course, Lesson, Enrollment, Progress |
| Schemas | `config/schemas.py` | Pydantic/Django Ninja schemas untuk request/response validation |
| API Routers | `config/apiv1.py` | Router auth, courses, lessons, enrollments, general |
| Settings | `config/settings.py` | Database, media, Redis cache/session, Celery |
| Celery | `config/celery.py`, `lms/tasks.py` | Async task configuration and demo task |
| Docker | `Dockerfile`, `docker-compose.yml` | Container runtime |
| Postman | `postman/simple-lms-advanced.postman_collection.json` | Manual API testing collection |

API utama dipasang melalui:

```text
/api/
```

Swagger UI:

```text
/api/docs
```

## Testing Summary

Automated tests ditambahkan pada `lms/tests.py`.

Coverage:

- RBAC untuk admin, instructor, student, dan anonymous.
- Lesson CRUD.
- Enrollment untuk student.
- Progress validation agar lesson harus berasal dari course enrollment.

Perintah menjalankan test:

```bash
docker compose exec web python manage.py test lms
```

Manual testing dapat dilakukan melalui:

- Swagger UI di `http://localhost:8000/api/docs`
- Postman collection di `postman/simple-lms-advanced.postman_collection.json`

## Screenshots Placeholders

Tambahkan screenshot final pada bagian berikut saat laporan dikumpulkan:

### Docker Compose Running

Placeholder: `img/docker-ps.png`

### Swagger UI

Placeholder: `img/swagger.png`

### PostgreSQL / Django Migration

Placeholder: `img/migration.png`

### Postman Testing

Placeholder: tambahkan screenshot request auth, course, lesson, enrollment, dan progress.

### Redis Verification

Placeholder:

- `img/redis-ping.png`
- `img/redis-monitor.png`
- `img/redis-keys.png`
- `img/popular-courses.png`

### Automated Test Result

Placeholder: tambahkan screenshot hasil `python manage.py test lms`.

## Conclusion

Simple LMS telah memenuhi requirement wajib UAS: Docker Compose, PostgreSQL, JWT Authentication, Swagger, RBAC, Course CRUD, Lesson CRUD, Enrollment, Progress, dan README.

Project tetap mempertahankan arsitektur existing dan hanya melengkapi fitur backend mandatory yang belum tersedia. Dokumentasi, Postman collection, `.env.example`, dan automated tests sudah disesuaikan dengan implementasi backend saat ini.
