"""Seed reproducible demo data for coursework screenshots. Never run on production."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from onlinecourse.models import Choice, Course, Enrollment, Lesson, Question


class Command(BaseCommand):
    help = "Create demo admin, student, lessons, questions and choices."

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", required=True)
        parser.add_argument("--student-password", required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        if len(options["admin_password"]) < 8 or len(options["student_password"]) < 8:
            raise CommandError("Demo passwords must each be at least 8 characters.")
        admin, _ = User.objects.get_or_create(username="admin")
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(options["admin_password"])
        admin.save()

        student, _ = User.objects.get_or_create(username="demo", defaults={"first_name": "Demo"})
        student.set_password(options["student_password"])
        student.save()

        course, _ = Course.objects.update_or_create(
            name="Django Web Development",
            defaults={
                "description": "Learn how Django models, views and templates work together. "
                               "Complete a short exam and get instant grading.",
            },
        )
        lesson, _ = Lesson.objects.update_or_create(
            course=course, order=0,
            defaults={
                "title": "Building Web Applications with Django",
                "content": "Django is a Python web framework. A model defines the data, "
                           "a view handles a request, and a template renders HTML. "
                           "Use the ORM to work with databases through Python.",
            },
        )
        questions = [
            ("Which Python framework powers this website?",
             ["Django", "Flask", "FastAPI"], "Django"),
            ("What does HTML stand for?",
             ["HyperText Markup Language", "High Transfer Machine Language", "Hyperlink Template Model"],
             "HyperText Markup Language"),
            ("What does ORM stand for?",
             ["Object-Relational Mapping", "Online Request Module", "Object Render Manager"],
             "Object-Relational Mapping"),
        ]
        for question_text, options_, answer in questions:
            question, _ = Question.objects.update_or_create(
                lesson=lesson, question_text=question_text, defaults={"grade": 10},
            )
            for option in options_:
                Choice.objects.update_or_create(
                    question=question, choice_text=option,
                    defaults={"is_correct": option == answer},
                )
        _, created = Enrollment.objects.get_or_create(
            user=student, course=course, defaults={"mode": Enrollment.HONOR}
        )
        if created:
            Course.objects.filter(pk=course.pk).update(total_enrollment=F("total_enrollment") + 1)
        self.stdout.write(self.style.SUCCESS(
            f"Demo ready. Course ID: {course.pk}. Admin username: admin. Student username: demo."
        ))
