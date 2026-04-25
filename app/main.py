from fastapi import FastAPI
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



    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "operational",
            "environment": settings.APP_ENV
        }

    return app

app = create_app()
