from fastapi import APIRouter

from app.api.v1 import api_keys, auth, chat, documents
from app.evaluation.api import router as eval_router


router = APIRouter(prefix="/api/v1")
router.include_router(api_keys.router)
router.include_router(auth.router)
router.include_router(documents.router)
router.include_router(chat.router)
router.include_router(eval_router)