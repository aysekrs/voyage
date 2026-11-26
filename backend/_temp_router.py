from fastapi import APIRouter

router = APIRouter()

from fastapi import FastAPI as OriginalFastAPI

def FastAPI(*args, **kwargs):
    return router

def _include_router(other_router):
    router.include_router(other_router)

router.include_router = _include_router
