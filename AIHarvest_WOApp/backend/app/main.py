from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
import time

from .config import get_settings
from .database import init_db, check_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-assisted preventive maintenance system for asset management",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Catch-all for unhandled exceptions.
#
# This is deliberately a middleware and not an @app.exception_handler(Exception).
# Starlette installs a handler registered against Exception on ServerErrorMiddleware,
# which wraps CORSMiddleware from the outside -- so its response goes out with no
# Access-Control-Allow-Origin header. The browser then blocks it, and the caller
# sees an opaque "Network Error" with no status instead of the real message.
#
# Registration order matters: add_middleware() prepends, so whatever is registered
# FIRST ends up innermost. This must stay above the CORSMiddleware call below so
# that CORS wraps it and can attach the headers to the 500 on the way out.
#
# Handlers for specific exception classes (RequestValidationError, SQLAlchemyError)
# do not have this problem -- those run on the inner ExceptionMiddleware, already
# inside CORS -- so they are left as decorators further down.
@app.middleware("http")
async def catch_unhandled_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(f"Unexpected error handling {request.method} {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "message": "An unexpected error occurred"
            },
        )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Validation error occurred"
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": "Database error occurred"
        },
    )


# NOTE: the catch-all for bare Exception lives in catch_unhandled_exceptions
# above, as a middleware rather than a handler. See the comment there.


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Confidence Threshold: {settings.CONFIDENCE_THRESHOLD}")

    # Check database connection
    if check_db_connection():
        logger.info("Database connection verified")
    else:
        logger.warning("Database connection failed - check configuration")

    # Initialize database tables.
    #
    # Gated deliberately. create_all() only adds missing tables and never drops
    # or alters an existing one, but it is still DDL against a live database --
    # and it runs once per uvicorn worker on every restart. Deployments that
    # must not touch the schema set DB_AUTO_CREATE_TABLES=False and create
    # tables out of band with scripts/init_db.py. See deploy-app.sh.
    if settings.DB_AUTO_CREATE_TABLES:
        try:
            init_db()
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    else:
        logger.info(
            "DB_AUTO_CREATE_TABLES=False - skipping automatic table creation; "
            "this process will make no schema changes to the database"
        )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API is running.
    Returns application status and database connectivity.
    """
    db_status = check_db_connection()

    return {
        "status": "healthy" if db_status else "degraded",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected" if db_status else "disconnected",
        "db_auto_create_tables": settings.DB_AUTO_CREATE_TABLES,
        "llm_provider": settings.LLM_PROVIDER
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Import and register routers
from .routers import machines, work_orders, ai, workflow_logs, workflow_webhooks

app.include_router(machines.router, prefix=f"{settings.API_V1_PREFIX}/machines", tags=["Machines"])
app.include_router(work_orders.router, prefix=f"{settings.API_V1_PREFIX}/work-orders", tags=["Work Orders"])
app.include_router(ai.router, prefix=f"{settings.API_V1_PREFIX}/ai", tags=["AI"])
app.include_router(workflow_logs.router, prefix=f"{settings.API_V1_PREFIX}/workflow-logs", tags=["Workflow Logs"])
app.include_router(workflow_webhooks.router, prefix=f"{settings.API_V1_PREFIX}/workflows", tags=["Workflow Webhooks"])
