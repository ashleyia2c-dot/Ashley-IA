"""
conftest.py — Fixtures compartidos para los tests de Ashley.
"""
import os
import sys
import pytest

# Asegurar que el proyecto está en el path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
