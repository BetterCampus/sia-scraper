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
        startTime: Start time in "HH:MM" format
        endTime: End time in "HH:MM" format
        classroom: Classroom location (may be empty string)
    """

    day: str
    startTime: str
    endTime: str
    classroom: str


@dataclass
class Group:
    """Course group with teacher, schedules, and availability.

    Attributes:
        groupName: Group identifier (e.g., "1", "CA")
        teacher: Teacher name
        faculty: Faculty/school name
        courseName: Course name
        schedules: List of schedule entries
        duration: Duration string (e.g., "16 SEMANAS")
        scheduleType: Schedule type (e.g., "DIURNA")
        spots: Available spots (int or "NaN" if unavailable)
        code: Course code (optional)
    """

    groupName: str
    teacher: str
    faculty: str
    courseName: str
    schedules: list[Schedule]
    duration: str
    scheduleType: str
    spots: int | str
    code: str | None = None


@dataclass
class CourseInfo:
    """Complete course information including all groups and schedules.

    Attributes:
        courseName: Full course name
        credits: Credit hours
        typology: Course typology
        availableSpots: Total available spots across all groups
        scrapeTimestamp: Timestamp when data was scraped
        groups: List of course groups
        code: Course code (optional, set when scraping multiple)
    """

    courseName: str
    credits: int
    typology: str
    availableSpots: int
    scrapeTimestamp: str
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
        courseName: Course name with code
        code: Course code extracted from name
        credits: Credit hours
        typology: Course typology
        conditions: List of prerequisite conditions
    """

    courseName: str
    code: str
    credits: int
    typology: str
    conditions: list[PrereqCondition]
