"""Explainability and logging tool."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from app.config import BASE_DIR


def log_execution_trace(trace: Dict[str, Any]) -> None:
    """
    Log execution trace for observability and explainability.
    
    Args:
        trace: Dictionary containing execution trace information
    """
    log_dir = BASE_DIR / "app" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"execution_trace_{timestamp}.json"
    
    try:
        trace_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            **trace
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(trace_with_timestamp, f, indent=2, ensure_ascii=False)
        
        print(f"Execution trace logged to {log_file}")
    except IOError as e:
        print(f"Error logging execution trace: {e}")

