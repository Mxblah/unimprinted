import sys
from pathlib import Path

# Add the workspace root to sys.path so pytest can find modules
sys.path.insert(0, str(Path(__file__).parent))
