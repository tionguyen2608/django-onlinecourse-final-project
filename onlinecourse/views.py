from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import generic
from django.views.decorators.http import require_POST

from .models import Choice, Course, Enrollment, Submission


def registration_request(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.first_name = request.POST.get("firstname", "").strip()
        user.last_name = request.POST.get("lastname", "").strip()
        user.save()
        login(request, user)
        return redirect("onlinecourse:index")
    return render(request, "onlinecourse/user_registration_bootstrap.html", {"form": form})


def login_request(request):
    context = {}
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username"), password=request.POST.get("psw"))
        if user is not None:
            login(request, user)
            return redirect("onlinecourse:index")
        context["message"] = "Invalid username or password."
    return render(request, "onlinecourse/user_login_bootstrap.html", context)


@require_POST
def logout_request(request):
    logout(request)
    return redirect("onlinecourse:index")


def check_if_enrolled(user, course):
    return user.is_authenticated and Enrollment.objects.filter(user=user, course=course).exists()


class CourseListView(generic.ListView):
    template_name = "onlinecourse/course_list_bootstrap.html"
    context_object_name = "course_list"

    def get_queryset(self):
        courses = list(Course.objects.order_by("-total_enrollment", "pk"))
        for course in courses:
            course.is_enrolled = check_if_enrolled(self.request.user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_details_bootstrap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_enrolled"] = check_if_enrolled(self.request.user, self.object)
        context["questions"] = self.object.question_set.prefetch_related("choice_set")
        return context


@login_required
@require_POST
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    with transaction.atomic():
        _, created = Enrollment.objects.get_or_create(user=request.user, course=course, defaults={"mode": "honor"})
        if created:
            Course.objects.filter(pk=course.pk).update(total_enrollment=F("total_enrollment") + 1)
    return redirect("onlinecourse:course_details", pk=course.pk)


def extract_answers(request):
    answers = set()
    for key, values in request.POST.lists():
        if key.startswith("choice_"):
            answers.update(int(value) for value in values)
    return answers


@login_required
@require_POST
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    if enrollment is None:
        return HttpResponseForbidden("Enroll in this course before submitting an exam.")
    if not course.question_set.exists():
        return HttpResponseBadRequest("This course does not have an exam yet.")
    try:
        selected_ids = extract_answers(request)
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid choice identifier.")
    choices = list(Choice.objects.filter(pk__in=selected_ids, question__course=course))
    if {choice.pk for choice in choices} != selected_ids:
        return HttpResponseBadRequest("All choices must belong to this course.")
    with transaction.atomic():
        submission = Submission.objects.create(enrollment=enrollment)
        submission.choices.set(choices)
    return redirect("onlinecourse:show_exam_result", course_id=course.pk, submission_id=submission.pk)


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission.objects.select_related("enrollment"),
        pk=submission_id,
        enrollment__course=course,
        enrollment__user=request.user,
    )
    selected_ids = set(submission.choices.values_list("pk", flat=True))
    question_results = []
    earned_points = 0
    total_points = 0
    for question in course.question_set.prefetch_related("choice_set"):
        correct = question.is_get_score(selected_ids)
        total_points += question.grade
        if correct:
            earned_points += question.grade
        question_results.append({
            "question": question,
            "correct": correct,
            "earned": question.grade if correct else 0,
            "choices": [
                {"choice": choice, "selected": choice.pk in selected_ids}
                for choice in question.choice_set.all()
            ],
        })
    grade = round(100 * earned_points / total_points, 2) if total_points else 0
    return render(request, "onlinecourse/exam_result_bootstrap.html", {
        "course": course,
        "submission": submission,
        "grade": grade,
        "passed": total_points > 0 and grade >= 80,
        "earned_points": earned_points,
        "total_points": total_points,
        "question_results": question_results,
    })
