import logging
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.api.v1 import router as api_router
from app.core.config import BACKEND_DIR
from app.db.session import Base, ensure_database_schema, engine


def _setup_logging() -> None:
    log_dir = BACKEND_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── 文件日志（滚动，每个最多 10 MB，保留 5 个） ──
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # ── 控制台日志 ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # 抑制第三方库的调试日志
    for lib in ("chromadb", "sqlalchemy", "httpx", "httpcore", "urllib3", "watchfiles"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger("app").setLevel(logging.DEBUG)
    logging.getLogger(__name__).info("日志系统初始化完成 —— 日志文件：%s", log_dir / "app.log")


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_database_schema()
    yield


app = FastAPI(title="AI 文档问答助手 API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
