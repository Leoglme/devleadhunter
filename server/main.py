"""
Main FastAPI application entry point.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.router import router as api_router
from core.config import settings
from services.scraper_service import scraper_service
from scrappers.mock_scraper import MockScraper
from scrappers.google_scraper import GoogleScraper
from scrappers.pagesjaunes_scraper import PagesJaunesScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Initialize FastAPI app
app = FastAPI(
    title="Prospect Tool API",
    description="Personal prospect research tool API for freelance web developers",
    version="Hunter",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize services on application startup.
    
    This function runs when the FastAPI application starts.
    It sets up scrapers and other services.
    """
    # Initialize database and seed admin user
    from seeders.user_seeder import seed_admin_user
    seed_admin_user()
    
    # Register scrapers
    mock_scraper = MockScraper()
    await scraper_service.add_scraper(mock_scraper)
    print("[OK] Mock scraper registered")
    
    google_scraper = GoogleScraper()
    await scraper_service.add_scraper(google_scraper)
    print("[OK] Google scraper registered")
    
    pagesjaunes_scraper = PagesJaunesScraper()
    await scraper_service.add_scraper(pagesjaunes_scraper)
    print("[OK] Pages Jaunes scraper registered")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Cleanup on application shutdown.
    
    This function runs when the FastAPI application shuts down.
    It performs cleanup tasks.
    """
    print("Some services stopped")


@app.get("/", tags=["root"])
async def root() -> dict:
    """
    Root endpoint.
    
    Returns:
        Welcome message and API information
    """
    return {
        "message": "Welcome to Prospect Tool API",
        "version": "Hunter",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

