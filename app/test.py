import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
print(os.path.exists("app/static"))