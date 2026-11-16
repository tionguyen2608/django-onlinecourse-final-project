from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.timezone import now


class Instructor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_time = models.BooleanField(default=True)
    total_learners = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Learner(models.Model):
    STUDENT = "student"
    DEVELOPER = "developer"
    DATA_SCIENTIST = "data_scientist"
    DATABASE_ADMIN = "dba"
    OCCUPATION_CHOICES = [
        (STUDENT, "Student"),
        (DEVELOPER, "Developer"),
        (DATA_SCIENTIST, "Data Scientist"),
        (DATABASE_ADMIN, "Database Admin"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, default=STUDENT)
    social_link = models.URLField(blank=True)

    def __str__(self):
        return f"{self.user.username}, {self.get_occupation_display()}"


class Course(models.Model):
    name = models.CharField(max_length=100, default="Online course")
    image = models.ImageField(upload_to="course_images/", blank=True)
    description = models.CharField(max_length=1000)
    pub_date = models.DateField(null=True, blank=True)
    instructors = models.ManyToManyField(Instructor, blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Enrollment")
    total_enrollment = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        ordering = ["order", "pk"]

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    AUDIT = "audit"
    HONOR = "honor"
    BETA = "beta"
    COURSE_MODES = [(AUDIT, "Audit"), (HONOR, "Honor"), (BETA, "Beta")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=now)
    mode = models.CharField(max_length=5, choices=COURSE_MODES, default=AUDIT)
    rating = models.FloatField(default=5.0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "course"], name="unique_course_enrollment")]

    def __str__(self):
        return f"{self.user.username} - {self.course.name}"


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=500)
    grade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["pk"]

    def is_get_score(self, selected_ids):
        correct_ids = set(self.choice_set.filter(is_correct=True).values_list("id", flat=True))
        question_ids = set(self.choice_set.values_list("id", flat=True))
        selected_for_question = set(selected_ids) & question_ids
        return bool(correct_ids) and selected_for_question == correct_ids

    def __str__(self):
        return self.question_text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return self.choice_text


class Submission(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    choices = models.ManyToManyField(Choice, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission {self.pk} - {self.enrollment}"
