"""
services/exam_service.py - Online MCQ examination evaluation and lifecycle management.
"""

import logging
import random
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from extensions import db
from models.examination import Exam, Question, QuestionOption, ExamAttempt, AttemptAnswer
from models.student import Student

logger = logging.getLogger(__name__)


class ExamService:
    """Service handling exam lifecycle, student attempts, answer validation, and auto-scoring."""

    @staticmethod
    def check_exam_eligibility(exam_id: int, student_id: int) -> Tuple[bool, str]:
        """
        Validate whether a student is permitted to attempt an exam.
        Checks:
        - Exam existence and published/active status
        - Schedule time window (start_time <= now <= end_time)
        - Attempt limits
        """
        exam = Exam.query.get(exam_id)
        if not exam or exam.deleted_at:
            return False, "Examination not found."

        if exam.status not in ("published", "active"):
            return False, f"Examination is not currently active (Status: {exam.status})."

        now = datetime.utcnow()
        if exam.start_time and now < exam.start_time:
            return False, f"Examination has not started yet. Starts at {exam.start_time.isoformat()}."

        if exam.end_time and now > exam.end_time:
            return False, f"Examination has already concluded at {exam.end_time.isoformat()}."

        # Check existing attempts
        attempt_count = ExamAttempt.query.filter_by(
            exam_id=exam_id, student_id=student_id
        ).count()

        if attempt_count >= exam.max_attempts:
            return False, f"Maximum attempt limit ({exam.max_attempts}) reached."

        return True, "Eligible"

    @classmethod
    def start_attempt(cls, exam_id: int, student_id: int, ip_address: Optional[str] = None) -> Tuple[Optional[ExamAttempt], str]:
        """Begin an examination attempt for a student."""
        eligible, reason = cls.check_exam_eligibility(exam_id, student_id)
        if not eligible:
            return None, reason

        exam = Exam.query.get(exam_id)
        existing_in_progress = ExamAttempt.query.filter_by(
            exam_id=exam_id, student_id=student_id, status="in_progress"
        ).first()

        if existing_in_progress:
            return existing_in_progress, "Resuming ongoing attempt."

        current_count = ExamAttempt.query.filter_by(
            exam_id=exam_id, student_id=student_id
        ).count()

        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=student_id,
            started_at=datetime.utcnow(),
            status="in_progress",
            attempt_number=current_count + 1,
            ip_address=ip_address,
        )
        db.session.add(attempt)
        db.session.commit()
        return attempt, "Attempt started."

    @staticmethod
    def save_answer(attempt_id: int, question_id: int, selected_option_id: Optional[int]) -> AttemptAnswer:
        """Record or update a student's answer selection during an ongoing attempt."""
        attempt = ExamAttempt.query.get(attempt_id)
        if not attempt or attempt.status != "in_progress":
            raise ValueError("Attempt is not currently in progress.")

        answer = AttemptAnswer.query.filter_by(
            attempt_id=attempt_id, question_id=question_id
        ).first()

        if not answer:
            answer = AttemptAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                answered_at=datetime.utcnow(),
            )
            db.session.add(answer)
        else:
            answer.selected_option_id = selected_option_id
            answer.answered_at = datetime.utcnow()

        db.session.commit()
        return answer

    @classmethod
    def submit_attempt(cls, attempt_id: int, is_auto_submit: bool = False) -> ExamAttempt:
        """Finalize attempt and evaluate answers automatically."""
        attempt = ExamAttempt.query.get(attempt_id)
        if not attempt or attempt.status in ("submitted", "auto_submitted"):
            return attempt

        attempt.submitted_at = datetime.utcnow()
        attempt.status = "auto_submitted" if is_auto_submit else "submitted"

        if attempt.started_at:
            delta = attempt.submitted_at - attempt.started_at
            attempt.time_taken_minutes = max(1, int(delta.total_seconds() / 60))

        # Auto evaluate
        cls.auto_score(attempt_id)
        return attempt

    @staticmethod
    def auto_score(attempt_id: int) -> Dict[str, Any]:
        """Grade each answer against correct MCQ option and update total score & percentage."""
        attempt = ExamAttempt.query.get(attempt_id)
        if not attempt:
            raise ValueError("Attempt not found")

        exam = attempt.exam
        questions = exam.questions
        total_possible = sum(q.marks for q in questions) if questions else 0

        total_score = 0.0
        for q in questions:
            correct_opt = QuestionOption.query.filter_by(question_id=q.id, is_correct=True).first()
            answer = AttemptAnswer.query.filter_by(
                attempt_id=attempt_id, question_id=q.id
            ).first()

            if answer and answer.selected_option_id and correct_opt:
                if answer.selected_option_id == correct_opt.id:
                    answer.is_correct = True
                    answer.marks_obtained = float(q.marks)
                    total_score += float(q.marks)
                else:
                    answer.is_correct = False
                    answer.marks_obtained = 0.0
            elif answer:
                answer.is_correct = False
                answer.marks_obtained = 0.0

        attempt.score_obtained = total_score
        attempt.total_marks_attempted = total_possible
        percentage = round((total_score / total_possible * 100.0), 2) if total_possible > 0 else 0.0
        attempt.percentage = percentage
        attempt.is_passed = total_score >= (exam.passing_marks or 0)

        db.session.commit()
        return {
            "score": total_score,
            "total_marks": total_possible,
            "percentage": percentage,
            "is_passed": attempt.is_passed,
        }

    @staticmethod
    def get_exam_questions_for_student(exam_id: int, shuffle: bool = True) -> List[Dict[str, Any]]:
        """
        Return questions and shuffled options WITHOUT revealing which option is correct.
        Prevents frontend answer leakage.
        """
        exam = Exam.query.get(exam_id)
        if not exam:
            return []

        questions = list(exam.questions)
        if shuffle or exam.shuffle_questions:
            random.shuffle(questions)

        payload = []
        for idx, q in enumerate(questions, 1):
            options = list(q.options)
            if shuffle:
                random.shuffle(options)

            payload.append({
                "question_id": q.id,
                "order_number": idx,
                "question_text": q.question_text,
                "marks": q.marks,
                "options": [
                    {"option_id": opt.id, "option_text": opt.option_text}
                    for opt in options
                ],
            })

        return payload
