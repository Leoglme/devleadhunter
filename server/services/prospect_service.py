"""
Prospect data service.
"""
from typing import List, Optional
from models.prospect import Prospect, ProspectCreate, ProspectUpdate
from models.search import ProspectSearchRequest


class ProspectService:
    """
    Service for managing prospect data operations.
    
    This service handles CRUD operations and search functionality
    for prospects. Currently uses mock data, but can be extended
    to connect to a real database.
    """
    
    def __init__(self):
        """Initialize the prospect service."""
        self._prospects: List[Prospect] = []
        self._next_id: int = 1
    
    async def search_prospects(
        self, 
        request: ProspectSearchRequest
    ) -> List[Prospect]:
        """
        Search for prospects based on given criteria.
        
        Args:
            request: Search criteria including category, city, and max results
            
        Returns:
            List of matching prospects
            
        Example:
            >>> request = ProspectSearchRequest(category="restaurant", city="Paris")
            >>> results = await service.search_prospects(request)
        """
        filtered = self._prospects.copy()
        
        # Filter by category (partial match)
        if request.category:
            filtered = [
                p for p in filtered 
                if request.category.lower() in p.category.lower()
            ]
        
        # Filter by city
        if request.city:
            filtered = [
                p for p in filtered 
                if request.city.lower() in p.city.lower()
            ]
        
        # Limit results
        return filtered[:request.max_results]
    
    async def get_prospect(self, prospect_id: str) -> Optional[Prospect]:
        """
        Retrieve a prospect by ID.
        
        Args:
            prospect_id: Unique prospect identifier
            
        Returns:
            Prospect object if found, None otherwise
        """
        return next(
            (p for p in self._prospects if p.id == prospect_id),
            None
        )
    
    async def create_prospect(self, prospect: ProspectCreate) -> Prospect:
        """
        Create a new prospect.
        
        Args:
            prospect: Prospect data to create
            
        Returns:
            Created prospect with generated ID
        """
        new_prospect = Prospect(
            id=f"prospect_{self._next_id}",
            **prospect.model_dump()
        )
        self._prospects.append(new_prospect)
        self._next_id += 1
        return new_prospect
    
    async def update_prospect(
        self, 
        prospect_id: str, 
        update_data: ProspectUpdate
    ) -> Optional[Prospect]:
        """
        Update an existing prospect.
        
        Args:
            prospect_id: Prospect ID to update
            update_data: Fields to update
            
        Returns:
            Updated prospect if found, None otherwise
        """
        prospect = await self.get_prospect(prospect_id)
        if not prospect:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(prospect, field, value)
        
        return prospect
    
    async def delete_prospect(self, prospect_id: str) -> bool:
        """
        Delete a prospect.
        
        Args:
            prospect_id: Prospect ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        prospect = await self.get_prospect(prospect_id)
        if prospect:
            self._prospects.remove(prospect)
            return True
        return False


# Global service instance
prospect_service = ProspectService()

