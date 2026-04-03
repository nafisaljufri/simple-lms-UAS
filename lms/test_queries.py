from django.db import connection, reset_queries
from lms.models import Course


def run():
    print("=== N+1 QUERY ===")
    reset_queries()

    courses = Course.objects.all()
    for c in courses:
        print(c.instructor.username)

    print("Total queries:", len(connection.queries))


    print("\n=== OPTIMIZED QUERY ===")
    reset_queries()

    courses = Course.objects.select_related('instructor')
    for c in courses:
        print(c.instructor.username)

    print("Total queries:", len(connection.queries))