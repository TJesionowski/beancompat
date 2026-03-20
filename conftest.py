"""Root conftest: make implementations and strategies importable."""

import sys
from pathlib import Path

# Add project root to sys.path so imports like `strategies.accounts` work.
sys.path.insert(0, str(Path(__file__).parent))
