from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from .models import Choice, Course, Enrollment, Lesson, Question, Submission


class OnlineCourseExamTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user("student", password="strong-password-123")
        self.other = User.objects.create_user("other", password="strong-password-123")
        self.course = Course.objects.create(name="Django Basics", description="Test course")
        self.lesson = Lesson.objects.create(course=self.course, title="Basics", content="Content")
        self.q1 = Question.objects.create(lesson=self.lesson, question_text="Django?", grade=10)
        self.q2 = Question.objects.create(lesson=self.lesson, question_text="ORM?", grade=10)
        self.a1 = Choice.objects.create(question=self.q1, choice_text="Correct 1", is_correct=True)
        self.b1 = Choice.objects.create(question=self.q1, choice_text="Wrong 1", is_correct=False)
        self.a2 = Choice.objects.create(question=self.q2, choice_text="Correct 2", is_correct=True)
        self.b2 = Choice.objects.create(question=self.q2, choice_text="Wrong 2", is_correct=False)
        Enrollment.objects.create(user=self.student, course=self.course)
        self.client.force_login(self.student)

    def exam_url(self):
        return reverse("onlinecourse:submit", args=[self.course.pk])

    def test_models_and_question_grading(self):
        self.assertTrue(self.q1.is_get_score([self.a1.pk]))
        self.assertFalse(self.q1.is_get_score([self.a1.pk, self.b1.pk]))
        self.assertFalse(self.q2.is_get_score([]))

    def test_course_details_displays_exam_and_lessons(self):
        response = self.client.get(reverse("onlinecourse:course_details", args=[self.course.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Basics")
        self.assertContains(response, "Correct 1")

    def test_perfect_exam_passes_and_has_results(self):
        response = self.client.post(self.exam_url(), {
            f"question_{self.q1.pk}": [str(self.a1.pk)],
            f"question_{self.q2.pk}": [str(self.a2.pk)],
        })
        self.assertEqual(response.status_code, 302)
        submission = Submission.objects.get()
        self.assertTrue(submission.passed)
        self.assertEqual(submission.score, 20)
        self.assertEqual(submission.percentage, 100)
        response = self.client.get(response.url)
        self.assertContains(response, "Congratulations")
        self.assertContains(response, "Exam results")

    def test_wrong_answers_do_not_pass(self):
        self.client.post(self.exam_url(), {
            f"question_{self.q1.pk}": [str(self.b1.pk)],
            f"question_{self.q2.pk}": [str(self.a2.pk)],
        })
        submission = Submission.objects.get()
        self.assertFalse(submission.passed)
        self.assertEqual(submission.percentage, 50)

    def test_choices_from_other_course_do_not_count(self):
        other_course = Course.objects.create(name="Other", description="Other")
        other_lesson = Lesson.objects.create(course=other_course, title="Elsewhere", content="Else")
        other_question = Question.objects.create(lesson=other_lesson, question_text="Foreign")
        foreign_choice = Choice.objects.create(question=other_question, choice_text="Foreign", is_correct=True)
        self.client.post(self.exam_url(), {f"question_{self.q1.pk}": [
            str(self.a1.pk), str(foreign_choice.pk)]})
        submission = Submission.objects.get()
        self.assertNotIn(foreign_choice, submission.choices.all())

    def test_non_owner_cannot_view_results(self):
        self.client.post(self.exam_url(), {
            f"question_{self.q1.pk}": [str(self.a1.pk)],
        })
        submission = Submission.objects.get()
        self.client.force_login(self.other)
        url = reverse("onlinecourse:show_exam_result",
                      args=[self.course.pk, submission.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_exam_requires_enrollment(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.exam_url()).status_code, 404)

    def test_exam_requires_post(self):
        self.assertEqual(self.client.get(self.exam_url()).status_code, 405)
