from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def extract_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("当前仅支持 PDF、TXT 和 MD 文件")

    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        return "\n\f\n".join(page.extract_text() or "" for page in reader.pages).strip()

    return content.decode("utf-8-sig", errors="replace").strip()