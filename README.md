# Swiss Apartment Matcher

This tool helps match apartment search criteria with listings from various Swiss real estate websites including:
- Flatfox.ch
- Immobilier.ch
- Homegate.ch
- Immoscout24.ch
- Acheter-louer.ch
- Dreamo.ch
- Realadvisor.ch
- Facebook Marketplace
- Anibis.ch

## Features

- Scrapes multiple Swiss real estate websites for apartment listings
- Matches listings against user-defined search criteria
- Scores matches based on various factors (price, location, rooms, etc.)
- Provides a REST API for integration with other services

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
python main.py
```

2. The API will be available at `http://localhost:8000`

3. Use the `/search` endpoint with criteria like:
```json
{
    "location": "Lausanne",
    "min_price": 1000,
    "max_price": 2500,
    "min_rooms": 2,
    "max_rooms": 4,
    "min_size": 50,
    "max_size": 100,
    "property_types": ["apartment"],
    "features": ["balcony", "parking"]
}
```

## API Documentation

After starting the server, visit `http://localhost:8000/docs` for interactive API documentation.

## Project Structure

- `main.py`: FastAPI application and main entry point
- `models.py`: Pydantic models for data validation
- `matcher.py`: Logic for matching listings with search criteria
- `scrapers/`: Website-specific scraping implementations
  - `base_scraper.py`: Base scraper class
  - `flatfox_scraper.py`: Flatfox.ch scraper implementation
  - (Additional scrapers to be implemented)

## Contributing

Feel free to submit pull requests to add support for additional websites or improve the matching algorithm.

## License

MIT