"""
Quick startup test to verify the system can initialize.
This script checks configuration and database setup without starting the server.
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Test configuration loading
    from app.config import validate_config, GEMINI_API_KEY, DB_PATH, MEMORY_DIR
    
    print("Testing configuration...")
    try:
        validate_config()
        print(f"✓ Configuration valid (GEMINI_API_KEY: {'*' * 20 if GEMINI_API_KEY else 'NOT SET'})")
    except RuntimeError as e:
        print(f"✗ Configuration error: {e}")
        sys.exit(1)
    
    # Test database initialization
    print("\nTesting database setup...")
    from app.db.database import init_database
    init_database()
    print(f"✓ Database initialized at: {DB_PATH}")
    
    # Test directory creation
    print("\nTesting directory structure...")
    print(f"✓ Memory directory: {MEMORY_DIR}")
    print(f"✓ Database directory: {DB_PATH.parent}")
    
    # Test imports
    print("\nTesting imports...")
    from app.llm.planner import SalesAgentPlanner
    from app.llm.governance import GovernanceAgent
    from app.executor.validator import PlanValidator
    from app.executor.runner import PlanRunner
    print("✓ All core modules imported successfully")
    
    print("\n" + "=" * 60)
    print("✓ All startup checks passed!")
    print("=" * 60)
    print("\nYou can now start the server with:")
    print("  uvicorn app.main:app --reload")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

