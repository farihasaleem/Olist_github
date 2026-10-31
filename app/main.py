from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routers.analytics import router as analytics_router
from app.routers.tables import router as tables_router
from app.routers.auth import router as auth_router

app = FastAPI(
    title="Olist E-commerce Analytics API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(tables_router, prefix="/api/tables")


@app.get("/health")
def health():
    return {"status": "healthy"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")