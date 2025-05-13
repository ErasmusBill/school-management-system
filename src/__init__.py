from fastapi import FastAPI
from src.authservice.routes import auth_router
from src.db.main import init_db
from contextlib import asynccontextmanager
from src.admissionservice.routes import admission_router

version = "v1"


@asynccontextmanager
async def life_span(app: FastAPI):
    print(f"server is starting ...")   
    await init_db() 
    yield
    print(f"server is shutting down ...")

app = FastAPI(
    title="school management system",
    description="A simple school management system API",
    version="v1",
    lifespan=life_span
)

app.include_router(auth_router, prefix=f"/{version}/auth", tags=["auth"])
app.include_router(admission_router, prefix=f"/{version}/admission", tags=["admission"])