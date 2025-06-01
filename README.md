# Keypoints News Backend

A backend service that fetches news data using [PyGoogleNews](https://github.com/kotartemiy/pygooglenews), extracts content using Selenium, generates Inshorts-style summaries, and provides an API to access the data.

## Features

- REST API for fetching news data
- GitHub Actions workflow for scheduled news fetching
- Script for fetching news data and saving to JSON files
- Multiple news sources: top news, topics, search, geo
- Selenium-based image and content extraction
- Inshorts-style news summary generation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/keypoints-backend.git
cd keypoints-backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.sample`:
```bash
cp .env.sample .env
```

## Usage

### Running the API

Start the FastAPI server:

```bash
python -m app.main
```

The API will be available at http://localhost:8000 with documentation at http://localhost:8000/docs.

### API Endpoints

- `GET /` - API information
- `GET /top-news` - Get top news stories
- `GET /topic-headlines/{topic}` - Get headlines for a specific topic
- `GET /search?query={query}` - Search for news with a specific query
- `GET /geo/{location}` - Get news for a specific location

### Fetching News via Script

You can use the script to fetch news and save to a JSON file:

```bash
# Fetch top news
python scripts/fetch_news.py --type top --output data/news_top.json

# Fetch technology news
python scripts/fetch_news.py --type topic --topic technology --output data/news_tech.json

# Search for news with a query
python scripts/fetch_news.py --type search --query "artificial intelligence" --when 1d --output data/news_ai.json

# Get news for a specific location
python scripts/fetch_news.py --type geo --location "San Francisco" --output data/news_sf.json
```

### Generating Inshorts-style Summaries

The system can generate Inshorts-style summaries from news data:

```bash
# Process a single category
python scripts/generate_inshorts_selenium.py --input data/news_top.json --output data/inshorts_top.json --max-articles 5 --headless

# Process all categories at once
python scripts/generate_all_inshorts.py --input-dir data --output-dir data --max-articles 5 --headless
```

These scripts use Selenium to:
1. Extract proper images from original news sources
2. Generate concise summaries of articles
3. Resolve Google News redirect URLs to original sources
4. Save data in a structured JSON format

## GitHub Actions Workflow

The repository includes a GitHub Actions workflow that:

1. Runs automatically every 6 hours to fetch news data
2. Extracts images and content using Selenium
3. Generates Inshorts-style summaries for all news categories
4. Commits and pushes the updated data to the repository
5. Can be triggered manually with custom parameters

### Manual Trigger

You can manually trigger the workflow from the Actions tab in GitHub with the following parameters:

- News type: top, topic, search, or geo
- Topic (for topic news)
- Query (for search)
- When (for search, e.g., 1h, 1d)
- Location (for geo news)
- Output path (where to save the JSON file)

## Development

### Project Structure

```
keypoints-backend/
├── .github/
│   └── workflows/
│       └── fetch_news.yml       # GitHub Actions workflow
├── app/
│   ├── __init__.py
│   ├── api.py                   # FastAPI application
│   ├── main.py                  # Application entry point
│   └── news_service.py          # PyGoogleNews wrapper
├── data/
│   ├── news_*.json              # Raw news data
│   └── inshorts_*.json          # Processed Inshorts-style summaries
├── scripts/
│   ├── fetch_news.py            # Script for fetching news
│   ├── generate_all_inshorts.py # Process all news categories
│   ├── generate_inshorts_selenium.py # Generate Inshorts summaries
│   ├── selenium_news_extractor.py # Extract news content with Selenium
│   ├── test_installation.py     # Test dependencies installation
│   └── simple_test.py           # Simple functionality test
├── .env.sample                  # Sample environment variables
├── .gitignore
├── README.md
└── requirements.txt             # Project dependencies
```

## License

MIT 