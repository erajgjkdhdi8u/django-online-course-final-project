"""Course, enrollment, question, answer choice, and exam submission models."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Instructor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_time = models.BooleanField(default=True)
    total_learners = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username


class Learner(models.Model):
    STUDENT, DEVELOPER, DATA_SCIENTIST, DATABASE_ADMIN = (
        "student", "developer", "data_scientist", "dba"
    )
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
        return self.user.username


class Course(models.Model):
    name = models.CharField(max_length=100, default="Online course")
    image = models.ImageField(upload_to="course_images/", blank=True)
    description = models.TextField()
    pub_date = models.DateField(default=timezone.localdate)
    instructors = models.ManyToManyField(Instructor, blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Enrollment")
    total_enrollment = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    AUDIT, HONOR, BETA = "audit", "honor", "beta"
    COURSE_MODES = [(AUDIT, "Audit"), (HONOR, "Honor"), (BETA, "Beta")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=timezone.localdate)
    mode = models.CharField(max_length=5, choices=COURSE_MODES, default=AUDIT)
    rating = models.FloatField(default=5.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_course_enrollment")
        ]

    def __str__(self):
        return f"{self.user.username}: {self.course.name}"


class Question(models.Model):
    """Each lesson can have multiple exam questions, with weighted grade points."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=500)
    grade = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.question_text

    def is_get_score(self, selected_ids):
        """A multiple-choice question earns points only when the full answer set matches."""
        correct_ids = set(self.choice_set.filter(is_correct=True).values_list("id", flat=True))
        return bool(correct_ids) and correct_ids == set(int(pk) for pk in selected_ids)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=250)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.choice_text


class Submission(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    choices = models.ManyToManyField(Choice, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)

    def __str__(self):
        return f"Submission #{self.pk} ({self.enrollment.user.username})"
