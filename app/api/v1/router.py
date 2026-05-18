"""Main API router"""
from fastapi import APIRouter
from app.api.v1.endpoints import devices, data, auth

api_router = APIRouter()
api_router.include_router(devices.router)
api_router.include_router(data.router)
api_router.include_router(auth.router)
