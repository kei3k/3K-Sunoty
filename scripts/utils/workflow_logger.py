"""
Workflow logger for tracking remix attempts and results.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

try:
    from .logger import logger
except ImportError:
    from logger import logger


class WorkflowLogger:
    """Logs remix workflow attempts and results."""

    def __init__(self, log_dir: str = "output/logs"):
        """Initialize workflow logger."""
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.current_workflow = None

    def start_workflow(self, workflow_id: str, song_name: str, style: str):
        """Start logging a workflow."""
        self.current_workflow = {
            "workflow_id": workflow_id,
            "song_name": song_name,
            "style": style,
            "start_time": datetime.now().isoformat(),
            "attempts": [],
            "final_result": None
        }

        logger.info(f"Started workflow {workflow_id} for {song_name}")

    def log_attempt(self, attempt: int, data: Dict[str, Any]):
        """Log a remix attempt."""
        if self.current_workflow:
            attempt_log = {
                "attempt": attempt,
                "timestamp": datetime.now().isoformat(),
                **data
            }
            self.current_workflow["attempts"].append(attempt_log)

            logger.info(f"Logged attempt {attempt}: {data.get('status', 'unknown')}")

    def save_workflow(self, result: Dict[str, Any]) -> str:
        """Save complete workflow log."""
        if self.current_workflow:
            self.current_workflow["final_result"] = result
            self.current_workflow["end_time"] = datetime.now().isoformat()

            # Calculate total time
            start = datetime.fromisoformat(self.current_workflow["start_time"])
            end = datetime.fromisoformat(self.current_workflow["end_time"])
            self.current_workflow["total_time_seconds"] = (end - start).total_seconds()

            # Save to file
            log_file = os.path.join(
                self.log_dir,
                f"workflow_{self.current_workflow['workflow_id']}.json"
            )

            with open(log_file, 'w') as f:
                json.dump(self.current_workflow, f, indent=2)

            logger.info(f"Workflow log saved: {log_file}")
            return log_file

        return None


# Global workflow logger
workflow_logger = WorkflowLogger()
