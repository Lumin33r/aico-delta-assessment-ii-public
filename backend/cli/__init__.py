"""
CLI module for AI Personal Tutor.

Provides command-line tools for:
- demo: Full pipeline demonstration
"""

from .demo import main, run_demo, interactive_mode

__all__ = ['main', 'run_demo', 'interactive_mode']
