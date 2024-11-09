from typing import List, Dict
from models import SearchCriteria, PropertyListing, MatchResult

class PropertyMatcher:
    def __init__(self):
        self.criteria_weights = {
            'price': 0.3,
            'location': 0.25,
            'rooms': 0.2,
            'size': 0.15,
            'features': 0.1
        }

    def match_listings(self, criteria: SearchCriteria, listings: List[Dict]) -> List[MatchResult]:
        """
        Match property listings against search criteria
        Returns sorted list of MatchResult objects with match scores
        """
        results = []
        
        for listing_dict in listings:
            # Convert dictionary to PropertyListing
            listing = PropertyListing(**listing_dict)
            
            match_score = 0
            matching_criteria = []
            missing_criteria = []
            
            # Price matching
            if criteria.min_price is not None and criteria.max_price is not None:
                if criteria.min_price <= listing.price <= criteria.max_price:
                    match_score += self.criteria_weights['price']
                    matching_criteria.append('price_range')
                else:
                    missing_criteria.append('price_range')
            
            # Location matching (simple contains check)
            if criteria.location.lower() in listing.location.lower():
                match_score += self.criteria_weights['location']
                matching_criteria.append('location')
            else:
                missing_criteria.append('location')
            
            # Rooms matching
            if listing.rooms is not None and criteria.min_rooms is not None and criteria.max_rooms is not None:
                if criteria.min_rooms <= listing.rooms <= criteria.max_rooms:
                    match_score += self.criteria_weights['rooms']
                    matching_criteria.append('rooms')
                else:
                    missing_criteria.append('rooms')
            
            # Size matching
            if listing.size is not None and criteria.min_size is not None and criteria.max_size is not None:
                if criteria.min_size <= listing.size <= criteria.max_size:
                    match_score += self.criteria_weights['size']
                    matching_criteria.append('size')
                else:
                    missing_criteria.append('size')
            
            # Features matching
            if criteria.features and listing.features:
                matched_features = set(criteria.features) & set(listing.features)
                if matched_features:
                    feature_score = len(matched_features) / len(criteria.features)
                    match_score += self.criteria_weights['features'] * feature_score
                    matching_criteria.append('features')
                else:
                    missing_criteria.append('features')
            
            # Convert to percentage
            match_score = round(match_score * 100, 2)
            
            # Create MatchResult
            result = MatchResult(
                listing=listing,
                match_score=match_score,
                matching_criteria=matching_criteria,
                missing_criteria=missing_criteria
            )
            results.append(result)
        
        return results