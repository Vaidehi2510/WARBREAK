import os
import sys

# Make backend/ importable both locally and inside Vercel's function bundle.
HERE = os.path.dirname(os.path.abspath(__file__))
for backend_dir in (
    os.path.join(HERE, "backend"),
    os.path.join(os.path.dirname(HERE), "backend"),
    os.path.join(os.getcwd(), "backend"),
):
    if os.path.isdir(backend_dir) and backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

from main import app
