from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SearchCriteria(BaseModel):
    location: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rooms: Optional[float] = None
    max_rooms: Optional[float] = None
    min_size: Optional[float] = None
    max_size: Optional[float] = None
    features: Optional[List[str]] = None

class PropertyListing(BaseModel):
    title: str
    price: float
    location: str
    rooms: Optional[float] = None
    size: Optional[float] = None
    features: Optional[List[str]] = None
    link: str
    source: str
    created_at: datetime = datetime.now()

class MatchResult(BaseModel):
    listing: PropertyListing
    match_score: float
    matching_criteria: List[str]
    missing_criteria: List[str]