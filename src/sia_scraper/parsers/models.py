"""Dataclasses for SIA course data structures.

This module provides explicit type definitions for all course-related data
returned by SIA scraper functions, replacing implicit dict structures with
type-safe dataclasses.
"""

from dataclasses import dataclass


@dataclass
class Schedule:
    """Schedule entry for a course group.

    Attributes:
        day: Day of week (e.g., "LUNES", "MARTES")
        start_time: Start time in "HH:MM" format
        end_time: End time in "HH:MM" format
        classroom: Classroom location (may be empty string)
    """

    day: str
    start_time: str
    end_time: str
    classroom: str


@dataclass
class Group:
    """Course group with teacher, schedules, and availability.

    Attributes:
        group_name: Group identifier (e.g., "1", "CA")
        teacher: Teacher name
        faculty: Faculty/school name
        course_name: Course name
        schedules: List of schedule entries
        duration: Duration string (e.g., "16 SEMANAS")
        schedule_type: Schedule type (e.g., "DIURNA")
        spots: Available spots (None if unavailable)
        code: Course code (optional)
    """

    group_name: str
    teacher: str
    faculty: str
    course_name: str
    schedules: list[Schedule]
    duration: str
    schedule_type: str
    spots: int | None
    code: str | None = None


@dataclass
class CourseInfo:
    """Complete course information including all groups and schedules.

    Attributes:
        course_name: Full course name
        credits: Credit hours
        typology: Course typology
        available_spots: Total available spots across all groups
        scrape_timestamp: Timestamp when data was scraped
        groups: List of course groups
        code: Course code (optional, set when scraping multiple)
    """

    course_name: str
    credits: int
    typology: str
    available_spots: int
    scrape_timestamp: str
    groups: list[Group]
    code: str | None = None


@dataclass
class Prerequisite:
    """A prerequisite course.

    Attributes:
        course_code: Course code (e.g., "2016489")
        course_name: Course name
    """

    course_code: str
    course_name: str


@dataclass
class PrereqCondition:
    """Prerequisite condition with list of required courses.

    Attributes:
        condition: Condition type from SIA (e.g., "Must pass ALL")
        type: Condition type
        all_required: Whether all courses are required ("Si" or "No")
        number_of_courses: Number of required courses
        prerequisites: List of prerequisite courses
    """

    condition: str
    type: str
    all_required: str
    number_of_courses: str
    prerequisites: list[Prerequisite]


@dataclass
class CoursePrereqs:
    """Course prerequisites and enrollment conditions.

    Attributes:
        course_name: Course name with code
        code: Course code extracted from name
        credits: Credit hours
        typology: Course typology
        conditions: List of prerequisite conditions
    """

    course_name: str
    code: str
    credits: int
    typology: str
    conditions: list[PrereqCondition]
