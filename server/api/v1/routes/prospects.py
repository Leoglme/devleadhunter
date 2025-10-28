"""
Prospect management routes.
"""
from typing import List
from fastapi import APIRouter, HTTPException, status
from models.prospect import Prospect, ProspectCreate, ProspectUpdate
from models.search import ProspectSearchRequest, ProspectSearchResponse
from services.prospect_service import prospect_service
from services.scraper_service import scraper_service


router = APIRouter(
    prefix="/prospects",
    tags=["prospects"]
)


@router.post(
    "/search",
    response_model=ProspectSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for prospects",
    description="Search for prospects based on category, city, and other criteria"
)
async def search_prospects(
    request: ProspectSearchRequest
) -> ProspectSearchResponse:
    """
    Search for prospects matching the given criteria.
    
    Args:
        request: Search criteria including category, city, and max results
        
    Returns:
        ProspectSearchResponse with matching prospects and statistics
        
    Raises:
        HTTPException: If search fails
        
    Example:
        >>> POST /prospects/search
        {
            "category": "restaurant",
            "city": "Paris",
            "max_results": 20,
            "source": "pagesjaunes"
        }
    """
    try:
        print('Ok')
        # Run scrapers to get fresh data
        # request.source is already a Source enum
        source_value = request.source.value if request.source else None
        print(f"[DEBUG] Search request - source: {request.source}, source_value: {source_value}")
        print(f"[DEBUG] Request details - category: {request.category}, city: {request.city}, max_results: {request.max_results}")
        
        scraped_prospects = await scraper_service.scrape_all(
            category=request.category or "",
            city=request.city or "",
            max_results=request.max_results,
            source_filter=source_value
        )
        
        print(f"[DEBUG] Scraped {len(scraped_prospects)} prospects")
        
        # Save scraped prospects and convert to Prospect objects
        prospects = []
        for prospect_data in scraped_prospects:
            prospect = await prospect_service.create_prospect(prospect_data)
            prospects.append(prospect)

        print(f"[DEBUG] Prospects: {prospects}")
        
        # Calculate statistics
        has_website = sum(1 for p in prospects if p.website)
        without_website = len(prospects) - has_website
        
        return ProspectSearchResponse(
            total=len(prospects),
            prospects=prospects,
            has_website=has_website,
            without_website=without_website
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "",
    response_model=List[Prospect],
    summary="List all prospects",
    description="Get a list of all prospects"
)
async def list_prospects() -> List[Prospect]:
    """
    Get all prospects.
    
    Returns:
        List of all prospects
    """
    request = ProspectSearchRequest(max_results=1000)
    return await prospect_service.search_prospects(request)


@router.get(
    "/{prospect_id}",
    response_model=Prospect,
    summary="Get prospect by ID",
    description="Retrieve a specific prospect by its ID"
)
async def get_prospect(prospect_id: str) -> Prospect:
    """
    Get a prospect by ID.
    
    Args:
        prospect_id: Unique prospect identifier
        
    Returns:
        Prospect object
        
    Raises:
        HTTPException: If prospect not found
    """
    prospect = await prospect_service.get_prospect(prospect_id)
    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found"
        )
    return prospect


@router.post(
    "",
    response_model=Prospect,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prospect",
    description="Create a new prospect manually"
)
async def create_prospect(prospect: ProspectCreate) -> Prospect:
    """
    Create a new prospect.
    
    Args:
        prospect: Prospect data to create
        
    Returns:
        Created prospect with generated ID
    """
    return await prospect_service.create_prospect(prospect)


@router.put(
    "/{prospect_id}",
    response_model=Prospect,
    summary="Update a prospect",
    description="Update an existing prospect by ID"
)
async def update_prospect(
    prospect_id: str,
    update_data: ProspectUpdate
) -> Prospect:
    """
    Update a prospect.
    
    Args:
        prospect_id: Prospect ID to update
        update_data: Fields to update
        
    Returns:
        Updated prospect
        
    Raises:
        HTTPException: If prospect not found
    """
    prospect = await prospect_service.update_prospect(prospect_id, update_data)
    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found"
        )
    return prospect


@router.delete(
    "/{prospect_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prospect",
    description="Delete a prospect by ID"
)
async def delete_prospect(prospect_id: str) -> None:
    """
    Delete a prospect.
    
    Args:
        prospect_id: Prospect ID to delete
        
    Raises:
        HTTPException: If prospect not found
    """
    deleted = await prospect_service.delete_prospect(prospect_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found"
        )

