"""MorphMenu's dependency-free local conversion core."""

__version__ = "0.1.0"

from .detect import detect_file
from .planner import PlanningError, plan_file

__all__ = ["__version__", "detect_file", "plan_file", "PlanningError"]
