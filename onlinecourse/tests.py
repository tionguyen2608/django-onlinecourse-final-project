from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Choice, Course, Enrollment, Question, Submission


class AssessmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = get_user_model().objects.create_user(username="learner", password="test-only-password")
        cls.other = get_user_model().objects.create_user(username="other", password="test-only-password")
        cls.course = Course.objects.create(name="Assessment", description="Test course")
        cls.enrollment = Enrollment.objects.create(user=cls.learner, course=cls.course)
        cls.q1 = Question.objects.create(course=cls.course, question_text="Select both correct choices", grade=70)
        cls.a = Choice.objects.create(question=cls.q1, choice_text="Correct A", is_correct=True)
        cls.b = Choice.objects.create(question=cls.q1, choice_text="Correct B", is_correct=True)
        cls.wrong = Choice.objects.create(question=cls.q1, choice_text="Incorrect")
        cls.q2 = Question.objects.create(course=cls.course, question_text="One correct choice", grade=30)
        cls.c = Choice.objects.create(question=cls.q2, choice_text="Correct C", is_correct=True)
        cls.other_course = Course.objects.create(name="Other", description="Other course")
        other_question = Question.objects.create(course=cls.other_course, question_text="Unrelated")
        cls.foreign_choice = Choice.objects.create(question=other_question, choice_text="Foreign", is_correct=True)

    def setUp(self):
        self.client.force_login(self.learner)

    def submit_url(self, course=None):
        return reverse("onlinecourse:submit", args=[(course or self.course).pk])

    def answer_data(self, *choices):
        return {f"choice_{choice.pk}": str(choice.pk) for choice in choices}

    def result_url(self, submission):
        return reverse("onlinecourse:show_exam_result", args=[self.course.pk, submission.pk])

    def test_exact_match_is_required_for_multiple_answers(self):
        self.assertTrue(self.q1.is_get_score([self.a.pk, self.b.pk]))
        self.assertFalse(self.q1.is_get_score([self.a.pk]))
        self.assertFalse(self.q1.is_get_score([self.a.pk, self.b.pk, self.wrong.pk]))
        self.assertFalse(self.q1.is_get_score([]))

    def test_perfect_exam_is_saved_and_shows_success(self):
        response = self.client.post(self.submit_url(), self.answer_data(self.a, self.b, self.c), follow=True)
        submission = Submission.objects.get()
        self.assertEqual(submission.enrollment, self.enrollment)
        self.assertEqual(submission.choices.count(), 3)
        self.assertEqual(response.context["grade"], 100)
        self.assertTrue(response.context["passed"])
        self.assertContains(response, "Congratulations")
        self.assertContains(response, "Score: 100%")

    def test_weighted_grade_and_failing_result(self):
        response = self.client.post(self.submit_url(), self.answer_data(self.c), follow=True)
        self.assertEqual(response.context["grade"], 30)
        self.assertEqual(response.context["earned_points"], 30)
        self.assertFalse(response.context["passed"])
        self.assertNotContains(response, "Congratulations")

    def test_selecting_every_choice_does_not_earn_full_credit(self):
        response = self.client.post(self.submit_url(), self.answer_data(self.a, self.b, self.wrong, self.c), follow=True)
        self.assertEqual(response.context["grade"], 30)

    def test_unanswered_exam_receives_zero(self):
        response = self.client.post(self.submit_url(), {}, follow=True)
        self.assertEqual(response.context["grade"], 0)
        self.assertFalse(response.context["passed"])

    def test_anonymous_submission_requires_login(self):
        self.client.logout()
        response = self.client.post(self.submit_url(), {})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/onlinecourse/login/", response.url)
        self.assertEqual(Submission.objects.count(), 0)

    def test_enrollment_is_required(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.submit_url(), {}).status_code, 403)
        self.assertEqual(Submission.objects.count(), 0)

    def test_choices_from_another_course_are_rejected(self):
        response = self.client.post(self.submit_url(), self.answer_data(self.foreign_choice))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_invalid_identifier_is_rejected(self):
        self.assertEqual(self.client.post(self.submit_url(), {"choice_invalid": "not-an-id"}).status_code, 400)
        self.assertEqual(Submission.objects.count(), 0)

    def test_submission_requires_post(self):
        self.assertEqual(self.client.get(self.submit_url()).status_code, 405)

    def test_another_learner_cannot_read_a_result(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.result_url(submission)).status_code, 404)

    def test_result_must_match_its_course(self):
        submission = Submission.objects.create(enrollment=self.enrollment)
        url = reverse("onlinecourse:show_exam_result", args=[self.other_course.pk, submission.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_duplicate_enrollment_does_not_increment_twice(self):
        self.client.force_login(self.other)
        url = reverse("onlinecourse:enroll", args=[self.course.pk])
        self.client.post(url)
        self.client.post(url)
        self.course.refresh_from_db()
        self.assertEqual(Enrollment.objects.filter(user=self.other, course=self.course).count(), 1)
        self.assertEqual(self.course.total_enrollment, 1)

    def test_course_without_questions_cannot_be_submitted(self):
        empty = Course.objects.create(name="Empty", description="No exam")
        Enrollment.objects.create(user=self.learner, course=empty)
        self.assertEqual(self.client.post(self.submit_url(empty), {}).status_code, 400)

    def test_course_detail_displays_lessons_and_exam(self):
        self.course.lesson_set.create(title="First lesson", content="Lesson text")
        response = self.client.get(reverse("onlinecourse:course_details", args=[self.course.pk]))
        self.assertContains(response, "First lesson")
        self.assertContains(response, "Select both correct choices")
        self.assertContains(response, "Submit exam")
