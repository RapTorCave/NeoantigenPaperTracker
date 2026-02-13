"""
Launch the dashboard.
Usage: python3 launch.py
"""

import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "streamlit", "run", "dashboard.py",
    "--logger.level", "error",
    "--server.headless", "false",
], cwd=__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
