# Keypoints News Backend

A comprehensive news aggregation and processing backend service that fetches news from multiple sources, processes content with AI-powered summarization, and provides a REST API for accessing curated news data. Specifically optimized for Bengaluru and Indian audiences.

## Features

- **REST API**: FastAPI-based service with automatic documentation
- **Multi-source News Fetching**: Uses PyGoogleNews for top news, topics, search, and geo-based news
- **AI-Powered Summarization**: Generates Inshorts-style concise summaries using NLTK and newspaper3k
- **Selenium Content Extraction**: Extracts images and full content from news sources
- **Automated Workflows**: GitHub Actions for scheduled news fetching and processing
- **Database Integration**: Supabase integration for data persistence
- **Bengaluru-Focused**: Curated categories targeting Bengaluru and Indian audiences
- **Rate Limiting**: Built-in API rate limiting for production use

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

- `GET /` - API information and available endpoints
- `GET /top-news` - Get top news stories with optional AI summaries
- `GET /topic-headlines/{topic}` - Get headlines for supported topics (business, technology, entertainment, sports, health, science, world)
- `GET /search` - Search news with query parameters:
  - `query` (required): Search term
  - `when` (optional): Time period (1h, 1d, 7d, 1m, 1y)
  - `from_date` (optional): Start date (YYYY-MM-DD)
  - `to_date` (optional): End date (YYYY-MM-DD)
- `GET /geo/{location}` - Get location-specific news
- `GET /health` - API health check endpoint

All endpoints support optional query parameters:
- `include_summary=true` - Include AI-generated summaries
- `inshorts_style=true` - Format summaries in Inshorts style

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

## Automated News Processing

The system includes automated workflows for continuous news processing:

### GitHub Actions Workflow
- **Scheduled Execution**: Runs daily at 6 AM UTC
- **Multi-step Processing**: 
  1. Fetches news from configured categories
  2. Extracts content and images using Selenium
  3. Generates AI-powered summaries
  4. Uploads processed data to Supabase
  5. Commits updated JSON files to repository
- **Manual Triggers**: Can be triggered manually with custom parameters
- **Error Handling**: Robust error handling and logging throughout the pipeline

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
├── .github/workflows/
│   └── fetch_news.yml           # Automated news processing workflow
├── app/
│   ├── __init__.py
│   ├── api.py                   # FastAPI REST API endpoints
│   ├── db.py                    # Supabase database operations
│   ├── main.py                  # Application entry point
│   ├── news_service.py          # PyGoogleNews service wrapper
│   └── summarizer.py            # AI summarization service
├── data/
│   ├── news_*.json              # Raw news data by category
│   └── inshorts_*.json          # Processed summaries
├── scripts/
│   ├── fetch_news.py            # News fetching script
│   ├── generate_all_inshorts.py # Batch processing script
│   ├── generate_inshorts_selenium.py # Selenium-based content extraction
│   ├── push_inshorts_to_supabase.py # Database upload script
│   └── selenium_news_extractor.py # Content extraction utilities
├── tests/
│   ├── test_api.py              # API endpoint tests
│   └── test_news_service.py     # Service layer tests
├── main.py                      # Main orchestrator script
├── requirements.txt             # Python dependencies
└── .env.sample                  # Environment configuration template
```

### Key Categories (Bengaluru-focused)
- Bengaluru local news
- Indian technology and startups
- Indian entertainment and celebrity news
- Indian sports and politics
- Education and trending topics

## License

MIT 