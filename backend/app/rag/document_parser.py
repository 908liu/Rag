from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
}


def _convert_with_markitdown(filename: str, content: bytes) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError as error:
        raise ValueError("当前格式需要安装 MarkItDown 依赖") from error

    result = MarkItDown().convert_stream(
        BytesIO(content),
        file_extension=Path(filename).suffix.lower(),
    )
    return result.text_content.strip()


def extract_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("当前支持 TXT、MD、PDF、DOCX、PPTX、XLSX 和 HTML 文件")

    if extension == ".pdf":
        reader = PdfReader(BytesIO(content))
        return "\n\f\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if extension in {".txt", ".md"}:
        return content.decode("utf-8-sig", errors="replace").strip()

    return _convert_with_markitdown(filename, content)