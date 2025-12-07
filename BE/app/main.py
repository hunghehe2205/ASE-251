from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health_check

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Replace '*' with the specific origin if needed
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_check.router)


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
