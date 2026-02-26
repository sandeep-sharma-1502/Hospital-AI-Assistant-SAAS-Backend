from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.webrtc import router as webrtc_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webrtc_router)


@app.get("/health")
async def health():
    return {"status": "ok"}