from fastapi import FastAPI
from src.authservice.routes import auth_router
from src.db.main import init_db
from contextlib import asynccontextmanager
from src.admissionservice.routes import admission_router

version = "v1"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting...")
    try:
        await init_db()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise  # Re-raise the exception to fail fast in development
    
    yield
    
    print("Server is shutting down...")

app = FastAPI(
    title="School Management System",
    description="A simple school management system API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth_router, prefix=f"/{version}/auth", tags=["auth"])
app.include_router(admission_router, prefix=f"/{version}/admission", tags=["admission"])