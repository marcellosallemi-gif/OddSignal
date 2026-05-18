from fastapi import FastAPI

from backend.app.routers.health import router as health_router


app = FastAPI(title="Football Odds Monitor")
app.include_router(health_router)
