# Multi-Agent Retail System

Enterprise-style agentic AI system for retail domain (EY Techathon use case). This system demonstrates intelligent LLM orchestration, explainability, and robustness through a clean separation of concerns: LLM agents generate plans, deterministic tools execute business logic.

## Architecture Overview

### Agent & Tool Model

**LLM Agents (2 total):**
1. **Sales Agent (Planner)**: LLM-based planner that understands user intent and generates JSON action plans
2. **Governance Agent**: LLM-based validator that fixes invalid JSON plans while preserving intent

**Deterministic Tools (8 total):**
- `get_session_context` / `save_session_context`: File-based session memory
- `get_user_profile`: SQLite user data retrieval
- `check_inventory`: Inventory availability checks
- `recommend_products`: Rule-based product recommendations
- `apply_offers`: Loyalty tier discount calculations
- `calculate_payment`: Payment amount calculations
- `get_fulfillment_options`: Delivery/pickup options
- `log_execution_trace`: Execution logging for explainability

### Flow: Planner → Validator → Executor

1. **Planner**: LLM generates JSON plan from user message
2. **Validator**: Validates plan structure and tool availability
   - If invalid → triggers Governance Agent to fix
3. **Executor**: Runs tools sequentially based on plan

## Project Structure

```
app/
 ├── main.py                 # FastAPI application
 ├── config.py              # Configuration settings
 ├── llm/
 │   ├── client.py          # LLM client abstraction
 │   ├── planner.py         # Sales Agent (Planner)
 │   └── governance.py      # Governance Agent
 ├── executor/
 │   ├── validator.py       # Plan validation
 │   └── runner.py          # Plan execution
 ├── tools/
 │   ├── session.py         # Session context management
 │   ├── users.py           # User profile tool
 │   ├── inventory.py       # Inventory tool
 │   ├── recommendations.py # Recommendation tool
 │   ├── loyalty.py         # Loyalty & offers tool
 │   ├── payment.py         # Payment calculation tool
 │   ├── fulfillment.py     # Fulfillment options tool
 │   └── explainability.py  # Execution logging
 ├── db/
 │   └── retail.db          # SQLite database (auto-created)
 ├── memory/
 │   └── sessions/          # Session context files
 ├── logs/                  # Execution trace logs
 └── schemas/
     └── plan_schema.py     # Pydantic schemas
```

## Database Schema

The SQLite database includes:

- **users**: `user_id`, `name`, `loyalty_tier`
- **products**: `product_id`, `name`, `category`, `base_price`
- **inventory**: `sku`, `product_id`, `size`, `quantity`, `location`
- **orders**: `order_id`, `user_id`, `total_amount`, `status`, `created_at`

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Multi-Agent-System
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables** (REQUIRED):

**Option 1: Environment Variable (Recommended for deployment)**
```bash
# Linux/Mac
export GEMINI_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:GEMINI_API_KEY="your_api_key_here"

# Windows (CMD)
set GEMINI_API_KEY=your_api_key_here
```

**Option 2: .env file (For local development convenience)**
```bash
# Create .env file in the project root
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

**Important**: 
- Environment variables take precedence over `.env` file
- The application will fail to start if `GEMINI_API_KEY` is not set
- Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Never commit `.env` file to version control** (already in `.gitignore`)

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The application will be available at:
- **Frontend UI**: `http://localhost:8000/` (interactive demo interface)
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **API Info**: `http://localhost:8000/api`

The application will validate configuration on startup and fail fast with a clear error if the API key is missing.

## API Endpoints

### Main Endpoint

**POST `/sales-agent`**
- **Request**:
```json
{
  "session_id": "session_123",
  "user_id": "user_456",
  "message": "I want to check if product PROD-001 in size M is available"
}
```
- **Response**:
```json
{
  "response": "The product is available! Quantity: 10, Location: warehouse",
  "execution_trace": {
    "plan": {...},
    "validation_passed": true,
    "execution_steps": [...],
    "final_result": {...}
  }
}
```

### Admin Endpoints (Data Ingestion)

**POST `/admin/users`**
```json
{
  "user_id": "user_001",
  "name": "John Doe",
  "loyalty_tier": "gold"
}
```

**POST `/admin/products`**
```json
{
  "product_id": "PROD-001",
  "name": "Wireless Headphones",
  "category": "electronics",
  "base_price": 99.99
}
```

**POST `/admin/inventory`**
```json
{
  "sku": "SKU-001",
  "product_id": "PROD-001",
  "size": "M",
  "quantity": 50,
  "location": "warehouse"
}
```

**POST `/admin/orders`**
```json
{
  "order_id": "ORD-001",
  "user_id": "user_001",
  "total_amount": 99.99,
  "status": "pending",
  "created_at": "2024-01-01T00:00:00"
}
```

## Testing the System

### Using the Web Frontend

1. Start the server: `uvicorn app.main:app --reload`
2. Open your browser: `http://localhost:8000/`
3. Fill in:
   - Session ID (e.g., `session_001`)
   - User ID (e.g., `user_001`)
   - Message (e.g., `Check if SKU-001 in size M is available`)
4. Click "Send to Sales Agent"
5. View the response and execution trace

### Using the API Directly

**Note**: For interactive testing, use the frontend UI or FastAPI docs at `/docs`. The `example_usage.py` script is available for development/testing but not required for demos.

#### 1. Populate Database

```bash
# Add a user
curl -X POST "http://localhost:8000/admin/users" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "name": "Alice",
    "loyalty_tier": "gold"
  }'

# Add a product
curl -X POST "http://localhost:8000/admin/products" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "PROD-001",
    "name": "Smart Watch",
    "category": "electronics",
    "base_price": 199.99
  }'

# Add inventory
curl -X POST "http://localhost:8000/admin/inventory" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "SKU-001",
    "product_id": "PROD-001",
    "size": "M",
    "quantity": 25,
    "location": "warehouse"
  }'
```

### 2. Use Sales Agent

```bash
curl -X POST "http://localhost:8000/sales-agent" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_001",
    "user_id": "user_001",
    "message": "Check if SKU-001 in size M is available"
  }'
```

## Key Features

✅ **Single LLM Agent**: Only one planner agent (Sales Agent)  
✅ **Clear Separation**: LLMs generate plans, tools execute logic  
✅ **Self-Healing**: Governance agent fixes invalid JSON  
✅ **Explainability**: Full execution traces logged  
✅ **Deterministic Tools**: All business logic in Python functions  
✅ **Enterprise-Ready**: Robust error handling and validation  
✅ **No Vector DBs**: Simple, efficient data storage  

## Configuration

Edit `app/config.py` to customize:
- Database path
- Memory directory
- LLM model and provider
- Available tools catalog

## Deployment

### Setting Environment Variables

**Local Development:**
```bash
# Linux/Mac
export GEMINI_API_KEY=your_api_key_here
uvicorn app.main:app --reload

# Windows PowerShell
$env:GEMINI_API_KEY="your_api_key_here"
uvicorn app.main:app --reload
```

**Production Deployment:**

The method depends on your hosting platform:

- **Heroku**: `heroku config:set GEMINI_API_KEY=your_key_here`
- **AWS/EC2**: Set in EC2 instance environment variables or use AWS Systems Manager Parameter Store
- **Docker**: `docker run -e GEMINI_API_KEY=your_key_here ...`
- **Kubernetes**: Set in ConfigMap or Secret
- **Railway/Render**: Set in platform's environment variables dashboard
- **Vercel/Netlify**: Set in Functions environment variables

**Important**: Never hardcode API keys in your code or commit them to version control.

## Development Notes

- **Environment Variables**: The system requires `GEMINI_API_KEY` to be set as an environment variable. The `.env` file is optional and only for local development convenience. Environment variables take precedence.
- **Real LLM Integration**: The system uses real Gemini API calls (no mocks). Temperature is set to 0.3 for consistent planning. Includes 15s timeout and 1 retry for transient failures.
- **Session Context**: Stored as JSON files in `app/memory/sessions/` with bounded growth (last 10 messages, 5 traces)
- **Execution Traces**: Logged to `app/logs/` for explainability
- **Database**: Auto-initialized on first run at `app/db/retail.db`
- **Frontend**: Simple HTML/JS interface for testing and demos (no frameworks required)
- **Governance Agent**: Includes semantic guardrails to prevent intent/steps modification
- **Parameter Validation**: Strict validation of required parameters per tool
- **Unanswerable Requests**: System gracefully handles requests that cannot be fulfilled with available tools

## Important: Ephemeral Storage (Render/Deployment)

**⚠️ Data Resets on Redeploy**

This prototype uses file-based storage (SQLite database and session files) which is **ephemeral** on platforms like Render:

- **SQLite database** (`app/db/retail.db`) resets on redeploy
- **Session memory** (`app/memory/sessions/*.json`) resets on redeploy  
- **Execution logs** (`app/logs/*.json`) reset on redeploy

**This is intentional for a hackathon prototype.** For production, you would use:
- Persistent database (PostgreSQL, MongoDB, etc.)
- Redis or similar for session storage
- Cloud logging service

**For demo purposes**: Data persistence is not required. The system demonstrates the agent orchestration, explainability, and self-healing capabilities regardless of data persistence.

## Additional Documentation

- **DEPLOYMENT.md**: Deployment checklist and judge Q&A guide

## License

This project is developed for EY Techathon.
