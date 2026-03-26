"""Pytest path bootstrap for local package imports."""

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_PARENT = os.path.dirname(ROOT)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if PROJECT_PARENT not in sys.path:
    sys.path.insert(0, PROJECT_PARENT)
