import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import API for FastAPI app
from app.api import app

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Run the application
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=port,
        reload=True
    ) 