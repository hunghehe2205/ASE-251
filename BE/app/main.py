from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db_client import connect_to_mongo, close_mongo_connection
from app.routers import auth, health_check, booking

app = FastAPI()


@app.on_event("startup")
async def startup_event() -> None:
    """Connect to MongoDB when the app starts."""
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Close MongoDB connection when the app stops."""
    await close_mongo_connection()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_check.router)
app.include_router(booking.router)


def main():
    """Run the FastAPI application."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
