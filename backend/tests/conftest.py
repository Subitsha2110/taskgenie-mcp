# conftest.py — shared pytest configuration
# Adds backend/ to sys.path so all imports resolve correctly during testing.

import sys
import os

# Ensure backend/ is on the path for all test modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
