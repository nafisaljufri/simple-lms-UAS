# Simple LMS - Release Notes

## Project Overview
Simple LMS is a RESTful API-based Learning Management System designed to handle core educational workflows. It provides a robust backend for managing courses, lessons, student enrollments, and progress tracking, with role-based access control for Admins, Instructors, and Students.

## Implemented Features
- **Authentication**: JWT-based login and registration for three roles (Admin, Instructor, Student).
- **Course Management**: Full CRUD operations for courses with image uploads, categorization, search, filtering, and pagination.
- **Lesson Management**: Full CRUD operations for lessons, including file attachment uploads and secure downloads.
- **Enrollment & Progress**: Students can enroll in courses and mark individual lessons as complete.
- **Dashboards**: Dedicated dashboards for students (tracking progress) and instructors (tracking student completion rates).
- **Popular Courses**: Real-time sorted leaderboard of popular courses powered by Redis.
- **Health Check**: Comprehensive `GET /api/health` endpoint detailing database, Redis, and Celery statuses.

## Architecture Summary
The project follows a standard modular Django structure:
- **`lms` App**: Contains all core models (`User`, `Category`, `Course`, `Lesson`, `Enrollment`, `Progress`) and their business logic.
- **`config` Module**: Houses the Django settings, Celery configuration, Pydantic schemas, and the Django Ninja `apiv1.py` router configurations.

The system employs PostgreSQL as the primary transactional database, Redis as the caching and session backend, and RabbitMQ as the message broker for Celery async tasks.

## Technology Stack
- **Core**: Python 3.11, Django 5.2.12, Django Ninja 1.1
- **Auth**: ninja-simple-jwt
- **Database**: PostgreSQL 15
- **Cache/Broker**: Redis 7, RabbitMQ 3
- **Async Workers**: Celery & Flower
- **Deployment**: Docker Compose

## API Overview
The API is exposed at `http://localhost:8000/api/`.
Interactive Swagger OpenAPI documentation is available at `http://localhost:8000/api/docs`.

### Key Endpoints
- `POST /api/auth/register` & `POST /api/auth/sign-in`
- `GET /api/courses` (Supports `?search=`, `?ordering=`, `?category=`)
- `GET /api/courses/popular`
- `GET /api/dashboard/student` & `GET /api/dashboard/instructor`
- `GET /api/health`

## Known Limitations
- The system currently only supports a single level of category hierarchy in the API representation, despite the model supporting self-referential relationships.
- File uploads (images/attachments) are stored in local volumes. In a scaled production environment, an S3-compatible backend (via `django-storages`) would be necessary.
- Email notifications for enrollments or completed courses are not yet implemented.

## How to Run
Ensure Docker Desktop is running, then execute:
```bash
docker compose up --build -d
```
The services will automatically start and connect. You must run migrations on the first startup:
```bash
docker compose exec web python manage.py migrate
```

## How to Seed Demo Data
To populate the database with a pre-configured instructor, student, category, course, and lessons, run the idempotent seed command:
```bash
docker compose exec web python manage.py seed_demo
```

## Demo Accounts
If you use the `seed_demo` command, the following accounts will be created:
- **Instructor**: `demo_instructor` / `demo123`
- **Student**: `demo_student` / `demo123`

Alternatively, you can register custom users via Swagger or Postman.
