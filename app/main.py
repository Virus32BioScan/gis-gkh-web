# app/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.routers import api as api_router

app = FastAPI(title="ГИС ЖКХ — Мини UI", version="0.2.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(api_router.router, prefix="/api", tags=["api"])

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "cfg": settings})
