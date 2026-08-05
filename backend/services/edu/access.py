"""Shared course-scoped authorization helpers for Education modules."""

from .models import Course, CourseMembership


def active_membership(course_id, user_id, role=None):
    query = CourseMembership.query.filter_by(
        course_id=course_id,
        user_id=user_id,
        status="active",
    )
    if role:
        query = query.filter_by(role=role)
    return query.first()


def active_course_for_member(course_id, user_id, role=None):
    if not active_membership(course_id, user_id, role):
        return None
    return Course.query.filter_by(id=course_id, status="active").first()


def is_teacher(course_id, user_id):
    return active_membership(course_id, user_id, "teacher") is not None

