import os
import tempfile
from pathlib import Path


_test_database = Path(tempfile.gettempdir()) / f"rag_web_ui_test_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_database.as_posix()}"
