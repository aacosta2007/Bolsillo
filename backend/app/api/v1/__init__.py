from fastapi import APIRouter

from app.api.v1 import accounts, auth, budgets, categories, goals, recurring, reports, transactions

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


for module in (auth, accounts, categories, transactions, budgets, recurring, goals, reports):
    api_router.include_router(module.router)
