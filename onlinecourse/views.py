"""Course pages, authentication, exam submission, and graded results."""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.views.decorators.http import require_POST

from .models import Choice, Course, Enrollment, Question, Submission


def registration_request(request):
    if request.method == "GET":
        return render(request, "onlinecourse/user_registration_bootstrap.html")
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])
    username = request.POST.get("username", "").strip()
    password = request.POST.get("psw", "")
    if not username or len(password) < 8:
        return render(request, "onlinecourse/user_registration_bootstrap.html",
                      {"message": "Enter a username and a password with at least 8 characters."})
    if User.objects.filter(username=username).exists():
        return render(request, "onlinecourse/user_registration_bootstrap.html",
                      {"message": "Username already exists."})
    user = User.objects.create_user(
        username=username, password=password,
        first_name=request.POST.get("firstname", ""),
        last_name=request.POST.get("lastname", ""),
    )
    login(request, user)
    return redirect("onlinecourse:index")


def login_request(request):
    if request.method == "GET":
        return render(request, "onlinecourse/user_login_bootstrap.html")
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])
    user = authenticate(
        request, username=request.POST.get("username", ""),
        password=request.POST.get("psw", "")
    )
    if user is None:
        return render(request, "onlinecourse/user_login_bootstrap.html",
                      {"message": "Invalid username or password."})
    login(request, user)
    return redirect("onlinecourse:index")


@require_POST
def logout_request(request):
    logout(request)
    return redirect("onlinecourse:index")


class CourseListView(generic.ListView):
    template_name = "onlinecourse/course_list_bootstrap.html"
    context_object_name = "course_list"

    def get_queryset(self):
        return Course.objects.order_by("-pub_date", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["enrolled_ids"] = set(Enrollment.objects.filter(
                user=self.request.user
            ).values_list("course_id", flat=True))
        return context


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_details_bootstrap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lessons"] = self.object.lesson_set.prefetch_related(
            "question_set__choice_set"
        ).all()
        context["is_enrolled"] = (
            self.request.user.is_authenticated
            and Enrollment.objects.filter(user=self.request.user, course=self.object).exists()
        )
        return context


@login_required
@require_POST
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    _, created = Enrollment.objects.get_or_create(
        user=request.user, course=course, defaults={"mode": Enrollment.HONOR}
    )
    if created:
        Course.objects.filter(pk=course.pk).update(total_enrollment=F("total_enrollment") + 1)
    return redirect("onlinecourse:course_details", pk=course.pk)


@login_required
@require_POST
@transaction.atomic
def submit(request, course_id):
    """Persist selected exam choices belonging to this course and calculate the score."""
    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    questions = list(Question.objects.filter(
        lesson__course=course
    ).prefetch_related("choice_set"))
    if not questions:
        return redirect("onlinecourse:course_details", pk=course.pk)

    permitted_choice_ids = set(Choice.objects.filter(
        question__lesson__course=course
    ).values_list("id", flat=True))
    all_selected = set()
    earned = 0
    total = sum(question.grade for question in questions)

    for question in questions:
        raw_ids = request.POST.getlist(f"question_{question.pk}")
        selected_ids = {int(pk) for pk in raw_ids if pk.isdecimal()}
        selected_ids &= permitted_choice_ids
        question_choices = {choice.pk for choice in question.choice_set.all()}
        selected_ids &= question_choices
        all_selected.update(selected_ids)
        if question.is_get_score(selected_ids):
            earned += question.grade

    percent = round(earned / total * 100, 2) if total else 0
    submission = Submission.objects.create(
        enrollment=enrollment,
        score=earned,
        max_score=total,
        percentage=percent,
        passed=percent >= 70,
    )
    submission.choices.set(all_selected)
    return redirect("onlinecourse:show_exam_result",
                    course_id=course.pk, submission_id=submission.pk)


@login_required
def show_exam_result(request, course_id, submission_id):
    """Only the learner who submitted the exam may see its result."""
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission, pk=submission_id,
        enrollment__course=course, enrollment__user=request.user,
    )
    selected = set(submission.choices.values_list("id", flat=True))
    questions = Question.objects.filter(lesson__course=course).select_related(
        "lesson"
    ).prefetch_related("choice_set")
    exam_results = []
    for question in questions:
        choices = list(question.choice_set.all())
        chosen = [choice for choice in choices if choice.pk in selected]
        correct = [choice for choice in choices if choice.is_correct]
        exam_results.append({
            "question": question,
            "user_choices": chosen,
            "correct_choices": correct,
            "is_correct": bool(correct) and {c.pk for c in chosen} == {c.pk for c in correct},
        })
    return render(request, "onlinecourse/exam_result_bootstrap.html", {
        "course": course,
        "submission": submission,
        "exam_results": exam_results,
        "grade": submission.percentage,
        "passed": submission.passed,
    })
