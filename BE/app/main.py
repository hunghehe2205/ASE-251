from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health_check, auth

app = FastAPI()

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "ASE-251 FastAPI Backend is running 🚀",
        "docs": "/docs"
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # update later for FE deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_check.router)
app.include_router(auth.router)


def main():
    """Run the FastAPI application."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
