from fastapi import APIRouter

from .authentications.views import router as auth_router


router = APIRouter(prefix="/v1")

router.include_router(auth_router)
