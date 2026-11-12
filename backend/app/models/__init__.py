"""ORM Models for MachineSense.

Exports Machine and Analysis SQLAlchemy models.
"""

from pathlib import Path
import sys

# Support root directory resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.app.models.models import Machine, Analysis
except ImportError:
    try:
        from app.models.models import Machine, Analysis
    except ImportError:
        from .models import Machine, Analysis

__all__ = ["Machine", "Analysis"]
