"""SIA Session State Enumeration.

This module defines the SiaSessionStatus enum representing the current state
of a SIA scraping session.
"""

from enum import Enum


class SiaSessionStatus(Enum):
    """Represents the current state of a SIA scraping session.

    The SIA system requires sequential navigation through different pages.
    State transitions are enforced by SiaSession to maintain valid navigation.

    ## Valid Transitions
        NO_SESSION → CAREER_NOT_SET: After calling create_session()
        CAREER_NOT_SET → ON_CAREER_PAGE: After calling set_career()
        ON_CAREER_PAGE → ON_COURSE_PAGE: After selecting a course
        ON_COURSE_PAGE → ON_CAREER_PAGE: After navigating back
        Any state → NO_SESSION: After calling close_session()
    """

    NO_SESSION = "NO_SESSION"
    CAREER_NOT_SET = "CAREER_NOT_SET"
    ON_CAREER_PAGE = "ON_CAREER_PAGE"
    ON_COURSE_PAGE = "ON_COURSE_PAGE"
