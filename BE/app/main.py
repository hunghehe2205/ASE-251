from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health_check, auth
from app.database.db_client import connect_to_mongo, close_mongo_connection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Replace '*' with the specific origin if needed
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()


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
