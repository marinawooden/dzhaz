from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles

from routers.music import router as music_routes

# overall fastapi instance
app = FastAPI(title="my app root")

# music routes
app.mount('/api', music_routes)

# static files mount
app.mount("/", StaticFiles(directory="public", html=True), name="public")

