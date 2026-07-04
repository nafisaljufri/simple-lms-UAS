from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lms.models import Category, Course, Lesson, Enrollment, Progress

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed database with demo data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding demo data...')
        
        # 1. Demo Instructor
        instructor, created = User.objects.get_or_create(
            username='demo_instructor',
            defaults={
                'role': 'instructor'
            }
        )
        if created:
            instructor.set_password('demo123')
            instructor.save()
            self.stdout.write(self.style.SUCCESS('Created demo instructor'))
        else:
            self.stdout.write('Demo instructor already exists')

        # 2. Demo Student
        student, created = User.objects.get_or_create(
            username='demo_student',
            defaults={
                'role': 'student'
            }
        )
        if created:
            student.set_password('demo123')
            student.save()
            self.stdout.write(self.style.SUCCESS('Created demo student'))
        else:
            self.stdout.write('Demo student already exists')

        # 3. Category
        category, created = Category.objects.get_or_create(
            name='Web Development'
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created category'))
        else:
            self.stdout.write('Category already exists')

        # 4. Demo Course
        course, created = Course.objects.get_or_create(
            title='Demo Fullstack Web Development',
            defaults={
                'description': 'A complete guide to modern web development.',
                'instructor': instructor,
                'category': category
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created demo course'))
        else:
            self.stdout.write('Demo course already exists')

        # 5. 3 Lessons
        lessons_data = [
            {'title': 'Introduction to HTML', 'content': 'Learn the basics of HTML.', 'order': 1},
            {'title': 'Styling with CSS', 'content': 'Make your websites beautiful.', 'order': 2},
            {'title': 'Interactive JS', 'content': 'Add interactivity to your site.', 'order': 3},
        ]
        
        for lesson_data in lessons_data:
            lesson, l_created = Lesson.objects.get_or_create(
                course=course,
                title=lesson_data['title'],
                defaults={
                    'content': lesson_data['content'],
                    'order': lesson_data['order']
                }
            )
            if l_created:
                self.stdout.write(self.style.SUCCESS(f"Created lesson: {lesson_data['title']}"))

        # 6. Enrollment
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created enrollment'))
        else:
            self.stdout.write('Enrollment already exists')

        # 7. Sample Progress
        # Let's get the first lesson
        first_lesson = Lesson.objects.filter(course=course, order=1).first()
        if first_lesson:
            progress, created = Progress.objects.get_or_create(
                student=student,
                lesson=first_lesson,
                defaults={
                    'completed': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created sample progress'))
            else:
                self.stdout.write('Sample progress already exists')
                
        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
