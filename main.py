import sys
from pathlib import Path

# Add the project root directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.ui.main import main

if __name__ == "__main__":
    main() 