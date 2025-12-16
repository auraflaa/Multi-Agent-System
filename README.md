# Multi-Agent Retail System

Enterprise-style agentic AI system for retail domain (EY Techathon use case). This system demonstrates intelligent LLM orchestration, explainability, and robustness through a clean separation of concerns: LLM agents generate plans, deterministic tools execute business logic.

## Architecture Overview

### Agent & Tool Model

**LLM Agents (2 total):**
1. **Sales Agent (Planner)**: LLM-based planner that understands user intent and generates JSON action plans
2. **Governance Agent**: LLM-based validator that fixes invalid JSON plans while preserving intent

**Deterministic Tools (10+ total):**
- `get_session_context` / `save_session_context`: File-based session memory
- `get_user_profile`: SQLite user data retrieval
- `update_user_name`: Update user name in database
- `update_personalization`: Save user preferences (gender, size, style, etc.)
- `check_inventory`: Inventory availability checks (by SKU or product_id)
- `recommend_products`: Rule-based product recommendations with gender filtering
- `apply_offers`: Loyalty tier discount calculations
- `calculate_payment`: Payment amount calculations
- `get_fulfillment_options`: Delivery/pickup options
- `log_execution_trace`: Execution logging for explainability

### Flow: Planner → Validator → Executor → Responder

1. **Planner**: LLM generates JSON plan from user message
2. **Validator**: Validates plan structure and tool availability
   - If invalid → triggers Governance Agent to fix
   - Auto-corrects product queries to include `recommend_products` step
3. **Executor**: Runs tools sequentially based on plan
4. **Responder**: Generates natural language response from tool results

## Project Structure

```
app/
 ├── main.py                 # FastAPI application
 ├── config.py              # Configuration settings
 ├── llm/
 │   ├── client.py          # LLM client abstraction
 │   ├── planner.py         # Sales Agent (Planner)
 │   ├── responder.py       # Response generator
 │   ├── prompts.py         # Centralized prompts
 │   └── governance.py      # Governance Agent
 ├── executor/
 │   ├── validator.py       # Plan validation
 │   └── runner.py          # Plan execution
 ├── tools/
 │   ├── session.py         # Session context & personalization management
 │   ├── users.py           # User profile tool
 │   ├── inventory.py       # Inventory tool
 │   ├── recommendations.py # Recommendation tool
 │   ├── loyalty.py         # Loyalty & offers tool
 │   ├── payment.py         # Payment calculation tool
 │   ├── fulfillment.py     # Fulfillment options tool
 │   ├── explainability.py  # Execution logging & workflow visualization
 │   └── tool_specs.py      # Tool parameter requirements
 ├── utils/
 │   └── size_mapping.py    # Size abbreviation mapping (M → Medium, etc.)
 ├── db/
 │   └── retail.db          # SQLite database (auto-created)
 ├── memory/
 │   ├── sessions/          # Session context files (per user)
 │   └── User/              # Personalization files (per user)
 ├── logs/                  # Execution trace logs
 ├── middleware/
 │   ├── auth.py            # API key authentication
 │   └── rate_limit.py      # Rate limiting
 └── schemas/
     └── plan_schema.py     # Pydantic schemas
```

## Database Schema

### SQLite Tables

**loyalty_tiers** (Lookup Table)
- `tier` (TEXT, PRIMARY KEY) - bronze, silver, gold, platinum
- `display_name` (TEXT, NOT NULL)
- `sort_order` (INTEGER, NOT NULL)

**users**
- `user_id` (TEXT, PRIMARY KEY)
- `name` (TEXT)
- `loyalty_tier` (TEXT) - References loyalty_tiers.tier

**categories**
- `category_id` (TEXT, PRIMARY KEY)
- `name` (TEXT, NOT NULL)

**products**
- `product_id` (TEXT, PRIMARY KEY)
- `name` (TEXT)
- `category` (TEXT)
- `base_price` (REAL) - Prices in INR
- `category_id` (TEXT, FOREIGN KEY → categories.category_id)

**inventory**
- `sku` (TEXT)
- `product_id` (TEXT, FOREIGN KEY → products.product_id)
- `size` (TEXT) - XS, S, M, L, XL, XXL
- `quantity` (INTEGER)
- `location` (TEXT)
- PRIMARY KEY (sku, size)

**orders**
- `order_id` (TEXT, PRIMARY KEY)
- `user_id` (TEXT, FOREIGN KEY → users.user_id)
- `total_amount` (REAL) - Amounts in INR
- `status` (TEXT)
- `created_at` (TEXT)

### File-Based Storage

**Session Memory**: `app/memory/sessions/{user_id}.json`
- Stores conversation history per user/session
- Structure: `{"sessions": {"session_id": {...}}}`

**Personalization**: `app/memory/User/{user_id}.json`
- Stores user preferences (gender, preferred_size, style_preferences, etc.)
- Example: `{"gender": "female", "preferred_size": "M"}`

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
- **Frontend UI**: `http://localhost:8000/` (interactive chat interface)
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Admin Console**: `http://localhost:8000/admin.html` (data management)
- **Health Check**: `http://localhost:8000/healthz`

## API Endpoints

### Main Endpoint

**POST `/sales-agent`**
- **Request**:
```json
{
  "session_id": "session_123",
  "user_id": "001",
  "message": "Find me female clothing"
}
```
- **Response**:
```json
{
  "response": "Here are some great options: Female Branded Top - ₹559.0...",
  "execution_trace": {
    "plan": {...},
    "validation_passed": true,
    "execution_steps": [...],
    "workflow_flow": [...],
    "final_result": {...}
  },
  "session_id": "session_123"
}
```

### Admin Endpoints (Data Management)

**POST `/admin/users`**
```json
{
  "user_id": "001",
  "name": "EY",
  "loyalty_tier": "bronze"
}
```

**POST `/admin/products`**
```json
{
  "product_id": "PROD-001",
  "name": "Female Branded Top",
  "category": "Women's Fashion",
  "base_price": 559.0
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

**POST `/admin/upload-csv/{table}** - Upload CSV data for users, products, inventory, categories, orders

**GET `/admin/db/{table}** - View all data in a table

**GET `/admin/memory/{user_id}** - View user's session memory

**DELETE `/admin/users/{user_id}** - Delete user and all associated data

**DELETE `/admin/session/{user_id}/{session_id}** - Delete specific session

### Health Check

**GET `/healthz`** - Health check endpoint for deployment platforms

## Security Configuration

### API Key Authentication (Optional)

Set an API key via environment variable:
```bash
export API_KEY=your-secret-api-key-here
```

**Note:** If `API_KEY` is not set, authentication is disabled (development mode). In production, always set an API key.

### CORS Configuration

Set allowed origins (comma-separated):
```bash
export ALLOWED_ORIGINS="http://localhost:8000,https://yourdomain.com"
```

If not set, defaults to `http://localhost:8000,http://127.0.0.1:8000`.

### Rate Limits

Default rate limits:
- `/sales-agent`: 30 requests per 60 seconds
- `/admin/*`: 20 requests per 60 seconds
- Other endpoints: 100 requests per 60 seconds

Rate limits are applied per client (identified by API key or IP address).

### Using API Keys

**Frontend (JavaScript)**:
```javascript
const apiKey = localStorage.getItem('api_key') || '';
const headers = { 'Content-Type': 'application/json' };
if (apiKey) {
    headers['X-API-Key'] = apiKey;
}
```

**cURL**:
```bash
curl -X POST 'http://127.0.0.1:8000/sales-agent' \
  -H 'X-API-Key: your-api-key-here' \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

## Deployment

### Render Deployment

1. Create new **Web Service** in Render dashboard
2. Set environment variables:
   - `GEMINI_API_KEY=your_key_here` (REQUIRED)
   - `API_KEY=your_secret_key` (optional, for authentication)
   - `ALLOWED_ORIGINS=your_domain.com` (optional)
   - `PYTHON_VERSION=3.11.9` (optional, but recommended)
3. Create `runtime.txt` with `3.11.9` (or set PYTHON_VERSION env var)
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Health check path: `/healthz`
7. Verify: Check logs for "Application Started" message

### Other Platforms

**Heroku**: `heroku config:set GEMINI_API_KEY=your_key_here`

**AWS/EC2**: Set in EC2 instance environment variables or use AWS Systems Manager Parameter Store

**Docker**: `docker run -e GEMINI_API_KEY=your_key_here ...`

**Kubernetes**: Set in ConfigMap or Secret

**Railway/Render**: Set in platform's environment variables dashboard

**Important**: Never hardcode API keys in your code or commit them to version control.

## Key Features

✅ **Intelligent Planning**: LLM-based planner extracts information and generates action plans  
✅ **Self-Healing**: Governance agent fixes invalid JSON while preserving intent  
✅ **Explainability**: Full execution traces with workflow visualization  
✅ **Deterministic Tools**: All business logic in Python functions  
✅ **Session Management**: Multi-session chat interface with conversation history  
✅ **Personalization**: Learns user preferences (gender, size, style) from conversations  
✅ **Gender Filtering**: Prevents mixing male/female products  
✅ **Size Mapping**: Supports both abbreviations (M) and full forms (Medium)  
✅ **Mobile-First UI**: Responsive chat interface inspired by GPT/Gemini  
✅ **Enterprise-Ready**: Robust error handling, validation, and security  
✅ **No Vector DBs**: Simple, efficient data storage  

## Development Notes

- **Environment Variables**: The system requires `GEMINI_API_KEY` to be set as an environment variable. The `.env` file is optional and only for local development convenience. Environment variables take precedence.
- **Real LLM Integration**: The system uses real Gemini API calls (no mocks). Temperature is set to 0.3 for consistent planning. Includes 15s timeout and 1 retry for transient failures.
- **Session Context**: Stored as JSON files in `app/memory/sessions/` with bounded growth (last 10 messages, 5 traces)
- **Personalization**: Stored separately in `app/memory/User/` for long-lived user preferences
- **Execution Traces**: Logged to `app/logs/` for explainability
- **Database**: Auto-initialized on first run at `app/db/retail.db`
- **Frontend**: Modern HTML/JS interface with markdown rendering, session management, and workflow visualization
- **Governance Agent**: Includes semantic guardrails to prevent intent/steps modification
- **Parameter Validation**: Strict validation of required parameters per tool
- **Currency**: All prices and amounts are in Indian Rupees (INR)

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

## Testing the System

### Using the Web Frontend

1. Start the server: `uvicorn app.main:app --reload`
2. Open your browser: `http://localhost:8000/`
3. Login with User ID (e.g., `001`)
4. Start chatting - the system will create sessions automatically
5. View execution traces and workflow visualization in the chat interface

### Using the API Directly

```bash
# Add a user
curl -X POST "http://localhost:8000/admin/users" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "001",
    "name": "EY",
    "loyalty_tier": "bronze"
  }'

# Use Sales Agent
curl -X POST "http://localhost:8000/sales-agent" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_001",
    "user_id": "001",
    "message": "Find me female clothing"
  }'
```

## Judge / Reviewer Q&A

### ❓ "Why not let the LLM call tools directly?"

**Answer:** "Direct tool calling hides failure modes and makes behavior harder to audit. We separate planning from execution so every action is validated, explainable, and recoverable."

### ❓ "Why do you need a governance agent?"

**Answer:** "LLMs are probabilistic. Rather than assuming perfect formatting, we added a constrained self-healing layer that fixes syntax errors without changing business intent."

### ❓ "Isn't this overkill for a prototype?"

**Answer:** "We intentionally kept the business logic simple, but made the orchestration robust. In enterprise systems, correctness and observability matter more than sophistication."

### ❓ "Why SQLite and file memory?"

**Answer:** "We separated structured enterprise data from conversational context. SQLite models realistic data access, while file-based session memory demonstrates continuity without infrastructure overhead."

### ❓ "What happens if the LLM generates invalid JSON?"

**Answer:** "Our governance agent fixes formatting errors while preserving semantic structure. We enforce strict guardrails: step count must match, action names must match, and intent must be preserved. If governance violates these constraints, we reject its output."

### ❓ "How do you handle LLM timeouts?"

**Answer:** "We set a 15-second timeout on all LLM requests and implement exactly one retry for transient failures. The retry only re-calls the planner, not the entire execution flow."

### ❓ "What about data persistence on Render?"

**Answer:** "We documented that SQLite and session files are ephemeral on Render. This is intentional for a hackathon prototype. For production, we would use PostgreSQL for structured data and Redis for session storage."

### ❓ "How do you ensure the planner doesn't invent tools?"

**Answer:** "We maintain a strict tool catalog. The validator rejects any action not in the catalog. The planner's prompt explicitly lists available tools with required parameters."

### ❓ "How do you prevent governance from changing user intent?"

**Answer:** "We enforce three hard guardrails: step count must match exactly, action names must match exactly, and intent must preserve word overlap. If governance violates any constraint, we reject its output."

## Known Limitations (Acceptable for Hackathon)

- ✅ SQLite + file memory are ephemeral (documented)
- ✅ Governance intent check is heuristic (acceptable)
- ✅ No concurrency hardening (not needed for demo)
- ✅ Planner quality depends on prompt (mitigated with validation)

These are **intentional tradeoffs** for a prototype, not bugs.

## License

This project is developed for EY Techathon.
