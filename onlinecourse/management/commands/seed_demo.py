import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate

from onlinecourse.models import Choice, Course, Instructor, Learner, Lesson, Question


class Command(BaseCommand):
    help = "Create a repeatable local demonstration course and administrator."

    @transaction.atomic
    def handle(self, *args, **options):
        password_path = Path(settings.BASE_DIR) / ".local-demo-password"
        password = os.environ.get("DEMO_ADMIN_PASSWORD")
        if not password:
            password = password_path.read_text().strip() if password_path.exists() else secrets.token_urlsafe(18)
            password_path.write_text(password)
            password_path.chmod(0o600)
        user, _ = get_user_model().objects.get_or_create(username="datadmin")
        user.first_name = "Dat"
        user.last_name = "Nguyen"
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        instructor, _ = Instructor.objects.get_or_create(user=user, defaults={"total_learners": 0})
        Learner.objects.get_or_create(user=user)
        course, _ = Course.objects.update_or_create(
            name="Django & Databases",
            defaults={
                "description": "Build a solid foundation in Django models, database relationships, and querying data with the ORM.",
                "pub_date": localdate(),
            },
        )
        course.instructors.add(instructor)
        lessons = [
            ("Django models", "A Django model is a Python class that describes stored data. Model fields define the columns, and migrations apply changes to the database."),
            ("Querying with the ORM", "The ORM connects Python code to database operations. Use filter() to retrieve a QuerySet containing records that match your conditions."),
            ("Model relationships", "ForeignKey describes a many-to-one relationship. ManyToManyField connects multiple records on both sides, such as submissions and selected choices."),
        ]
        for order, (title, content) in enumerate(lessons):
            Lesson.objects.update_or_create(course=course, order=order, defaults={"title": title, "content": content})
        exam = [
            ("What does Django's ORM connect?", 30, [
                ("Python objects and database tables", True),
                ("CSS styles and browser fonts", False),
                ("Image files and video clips", False),
            ]),
            ("What does QuerySet.filter() return?", 30, [
                ("A rendered HTML page", False),
                ("Only the first matching object", False),
                ("A QuerySet of matching records", True),
            ]),
            ("Which fields define relationships between Django models?", 40, [
                ("ForeignKey", True),
                ("ManyToManyField", True),
                ("A Bootstrap stylesheet", False),
            ]),
        ]
        for text, grade, choices in exam:
            question, _ = Question.objects.update_or_create(course=course, question_text=text, defaults={"grade": grade})
            for choice_text, is_correct in choices:
                Choice.objects.update_or_create(question=question, choice_text=choice_text, defaults={"is_correct": is_correct})
        self.stdout.write(self.style.SUCCESS("Demo course and administrator are ready. Username: datadmin."))
        self.stdout.write("Use DEMO_ADMIN_PASSWORD or the ignored .local-demo-password file for local login.")
