"""Reusable fixture factories for sia_scraper tests.

This module provides factory functions for creating test data structures
that can be used across multiple test files.
"""

from sia_scraper.parsers import CourseInfo, Group, Schedule


def create_course_info(
    course_name: str = "Test Course",
    credits: int = 3,
    typology: str = "DISCIPLINAR OBLIGATORIA",
    code: str = "1000001",
    available_spots: int = 50,
    groups: list[Group] | None = None,
) -> CourseInfo:
    """Create a CourseInfo object with default or custom values.

    Args:
        course_name: Full course name
        credits: Credit hours
        typology: Course typology
        code: Course code
        available_spots: Available spots
        groups: List of course groups

    Returns:
        CourseInfo instance
    """
    return CourseInfo(
        course_name=course_name,
        credits=credits,
        typology=typology,
        code=code,
        available_spots=available_spots,
        scrape_timestamp="2024-01-01 12:00",
        groups=groups or [],
    )


def create_group(
    group_name: str = "GRP-01",
    teacher: str = "Dr. Smith",
    faculty: str = "Faculty of Science",
    duration: str = "4 hours",
    schedule_type: str = "Presencial",
    spots: int = 30,
    schedules: list[Schedule] | None = None,
    course_name: str = "Test Course",
) -> Group:
    """Create a Group object with default or custom values.

    Args:
        group_name: Group identifier
        teacher: Instructor name
        faculty: Faculty/department
        duration: Class duration
        schedule_type: Type of schedule (Presencial, Virtual, etc.)
        spots: Available spots
        schedules: List of schedules
        course_name: Associated course name

    Returns:
        Group instance
    """
    return Group(
        group_name=group_name,
        teacher=teacher,
        faculty=faculty,
        course_name=course_name,
        schedules=schedules or [],
        duration=duration,
        schedule_type=schedule_type,
        spots=spots,
    )


def create_schedule(
    day: str = "LUNES",
    start_time: str = "10:00",
    end_time: str = "12:00",
    classroom: str = "101-101",
) -> Schedule:
    """Create a Schedule object with default or custom values.

    Args:
        day: Day of week
        start_time: Start time (HH:MM format)
        end_time: End time (HH:MM format)
        classroom: Room/building

    Returns:
        Schedule instance
    """
    return Schedule(
        day=day,
        start_time=start_time,
        end_time=end_time,
        classroom=classroom,
    )


def create_full_course_with_groups() -> CourseInfo:
    """Create a complete CourseInfo with typical group and schedule data.

    Returns:
        CourseInfo with populated groups and schedules
    """
    course_name = "Introduction to Computer Science"
    schedule = create_schedule(
        day="LUNES",
        start_time="10:00",
        end_time="12:00",
        classroom="101-101",
    )
    group = create_group(
        group_name="GRP-01",
        teacher="Dr. Smith",
        faculty="Faculty of Science",
        schedules=[schedule],
        course_name=course_name,
    )
    return create_course_info(
        course_name=course_name,
        credits=4,
        typology="DISCIPLINAR OBLIGATORIA",
        code="1000001",
        available_spots=30,
        groups=[group],
    )
