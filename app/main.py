from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.routers import auth, citizens, verify, ussd, audit, admin

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade API for Zambian National Identity Management",
        version="1.0.0",
        docs_url="/docs" if settings.APP_ENV != "production" else None,
        redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers
    app.include_router(auth.router, prefix="/api")
    app.include_router(citizens.router, prefix="/api")
    app.include_router(verify.router, prefix="/api")
    app.include_router(ussd.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    @app.get("/api")
    async def api_root():
        return {"status": "ok", "message": "ZamID Connect API v1"}



    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_msg = str(exc)
        stack_trace = traceback.format_exc()
        print(f"Global Exception: {error_msg}\n{stack_trace}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
                "detail": error_msg,
                "traceback": stack_trace if settings.APP_DEBUG else None
            }
        )

    return app

app = create_app()
