from fastapi import APIRouter

from app.api.v1.routes import auth, buildings, health, rules

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
