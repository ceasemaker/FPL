"""
FPL Platform Django Application

Loads Celery app on Django startup for task scheduling.
"""

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed yet (during build process)
    pass
