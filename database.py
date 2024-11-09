from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Listing(Base):
    __tablename__ = 'listings'
    
    id = Column(Integer, primary_key=True)
    source = Column(String)
    external_id = Column(String, unique=True)
    title = Column(String)
    price = Column(Float)
    location = Column(String)
    rooms = Column(Float)
    size = Column(Float)
    features = Column(JSON)
    images = Column(JSON)
    link = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    @classmethod
    def from_dict(cls, data: dict):
        """Create a Listing instance from a dictionary"""
        return cls(
            source=data['source'],
            external_id=data.get('external_id', data['link']),
            title=data['title'],
            price=data['price'],
            location=data['location'],
            rooms=data.get('rooms'),
            size=data.get('size'),
            features=json.dumps(data.get('features', [])),
            images=json.dumps(data.get('images', [])),
            link=data['link']
        )

class SearchProfile(Base):
    __tablename__ = 'search_profiles'
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String)
    criteria = Column(JSON)
    notification_frequency = Column(String)  # daily, hourly, realtime
    created_at = Column(DateTime, default=datetime.now)
    last_notification = Column(DateTime)

class Database:
    def __init__(self, db_url="sqlite:///apartments.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_listing(self, listing_data: dict):
        """Add or update a listing in the database"""
        listing = Listing.from_dict(listing_data)
        existing = self.session.query(Listing).filter_by(external_id=listing.external_id).first()
        
        if existing:
            # Update existing listing
            for key, value in listing_data.items():
                if key not in ['id', 'created_at']:
                    setattr(existing, key, value)
        else:
            # Add new listing
            self.session.add(listing)
        
        self.session.commit()

    def get_new_listings(self, since: datetime):
        """Get listings added since the given datetime"""
        return self.session.query(Listing).filter(Listing.created_at >= since).all()

    def add_search_profile(self, email: str, criteria: dict, frequency: str = "daily"):
        """Add a new search profile"""
        profile = SearchProfile(
            user_email=email,
            criteria=json.dumps(criteria),
            notification_frequency=frequency
        )
        self.session.add(profile)
        self.session.commit()

    def get_search_profiles(self, frequency: str = None):
        """Get all search profiles, optionally filtered by notification frequency"""
        query = self.session.query(SearchProfile)
        if frequency:
            query = query.filter_by(notification_frequency=frequency)
        return query.all()

    def update_notification_time(self, profile_id: int):
        """Update the last notification time for a search profile"""
        profile = self.session.query(SearchProfile).get(profile_id)
        if profile:
            profile.last_notification = datetime.now()
            self.session.commit()