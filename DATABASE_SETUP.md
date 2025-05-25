# Database Setup Guide

## PostgreSQL Database Configuration with Supabase

This application uses PostgreSQL to track brand analysis requests and their status. Follow these steps to set up your database:

### 1. Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to Settings > Database
3. Copy your connection details

### 2. Environment Variables

Add these variables to your `.env` file:

```env
# Database Configuration (Supabase PostgreSQL)
user=your_supabase_user
password=your_supabase_password  
host=your_supabase_host
port=5432
dbname=postgres

# Application Configuration
APP_NAME=mcp_brand_agent
PORT=8080

# API Keys (existing ones)
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true
OPENAI_API_KEY=your_openai_key
GROQ_API_KEY=your_groq_key
MCP_TOKEN=your_mcp_token
GOOGLE_API_KEY=your_google_api_key
```

### 3. Database Schema

The application automatically creates the required table on startup:

```sql
CREATE TABLE IF NOT EXISTS brand_analysis_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    brand_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    results JSONB,
    UNIQUE(user_id, session_id)
);
```

### 4. API Endpoints

#### Start Analysis
```bash
POST /query
{
    "userId": "user123",
    "sessionId": "session456", 
    "question": "Tesla",
    "brand_name": "Tesla"
}
```

Response:
```json
{
    "request_id": "uuid-here",
    "userId": "user123",
    "sessionId": "session456",
    "brand_name": "Tesla",
    "status": "running",
    "message": "Analysis started. Use the status endpoint to check progress."
}
```

#### Check Status
```bash
GET /status/{user_id}/{session_id}
```

Response (Running):
```json
{
    "request_id": "uuid-here",
    "userId": "user123",
    "sessionId": "session456", 
    "brand_name": "Tesla",
    "status": "running",
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-01T12:00:30"
}
```

Response (Completed):
```json
{
    "request_id": "uuid-here",
    "userId": "user123",
    "sessionId": "session456",
    "brand_name": "Tesla", 
    "status": "completed",
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-01T12:05:00",
    "results": {
        "analysis_results_twitter": {...},
        "analysis_results_linkedin": {...},
        "analysis_results_reddit": {...},
        "analysis_results_news": {...}
    }
}
```

Response (Failed):
```json
{
    "request_id": "uuid-here",
    "userId": "user123",
    "sessionId": "session456",
    "brand_name": "Tesla",
    "status": "failed",
    "created_at": "2024-01-01T12:00:00", 
    "updated_at": "2024-01-01T12:02:00",
    "error_message": "Error details here"
}
```

### 5. Status Values

- `running`: Analysis is in progress
- `completed`: Analysis finished successfully with results
- `failed`: Analysis failed with error message

### 6. Frontend Polling Pattern

```javascript
async function pollForResults(userId, sessionId) {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/status/${userId}/${sessionId}`);
            const data = await response.json();
            
            if (data.status === 'completed') {
                return data.results;
            } else if (data.status === 'failed') {
                throw new Error(data.error_message);
            }
            
            // Wait 5 seconds before next poll
            await new Promise(resolve => setTimeout(resolve, 5000));
            attempts++;
            
        } catch (error) {
            console.error('Polling error:', error);
            break;
        }
    }
    
    throw new Error('Analysis timed out');
}
```

### 7. Cleanup

The application includes an endpoint to clean up old requests:

```bash
DELETE /cleanup?days=7
```

This removes completed/failed requests older than the specified number of days. 