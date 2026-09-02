import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api import system, data, hotspots, model, predict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omniwatch")

app = FastAPI(
    title="OmniWatch API",
    description="Crime Intelligence & Predictive Safety Dashboard - backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # college project - not deployed publicly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(data.router, prefix="/api", tags=["data"])
app.include_router(hotspots.router, prefix="/api", tags=["hotspots"])
app.include_router(model.router, prefix="/api", tags=["model"])
app.include_router(predict.router, prefix="/api", tags=["predict"])


@app.get("/")
def root():
    return {"message": "OmniWatch API. See /docs for interactive API documentation."}
