from .users.router import router as user_router
from .competitions.router import router as competition_router
from .winners.router import router as winner_router

__all__ = [
    "user_router",
    "competition_router",
    "winner_router"
]
