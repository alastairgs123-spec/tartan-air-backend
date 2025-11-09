from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from auth import router as auth_router

# =====================================
# Database initialization
# =====================================
Base.metadata.create_all(bind=engine)

# =====================================
# App setup
# =====================================
app = FastAPI(
    title="Tartan Air Backend",
    description="API for Tartan Air — user accounts, authentication, routes, and more.",
    version="1.0.0"
)

# =====================================
# CORS (Cross-Origin Resource Sharing)
# =====================================
origins = [
    "*",  # you can restrict this later, e.g. to your frontend domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================
# Routers
# =====================================
app.include_router(auth_router)

# =====================================
# Root Endpoint
# =====================================
@app.get("/")
def root():
    return {"message": "Welcome to the Tartan Air Backend API ✈️"}


# =====================================
# Run (only used for local testing)
# =====================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
