import asyncio
import json

# Create an asyncio.Queue instance
log_queue = asyncio.Queue()

def get_log_queue() -> asyncio.Queue:
    """Returns the global log queue instance."""
    return log_queue

def format_log_record(record: dict) -> dict: # Add type hint for record
    """
    Formats a loguru log record (passed as a dictionary) into a dictionary for SSE.
    """
    return {
        "text": str(record['message']), # Ensure message is string
        "level": record['level'].name, # record['level'] is a loguru LevelObject
        "time": {
            "timestamp": record['time'].timestamp(), # record['time'] is a datetime object
            "repr": record['time'].isoformat()
        },
        "file": record['file'].path, # record['file'] is a loguru FileObject
        "line": record['line'],
        "name": record['name'],
        "function": record['function'],
        # Potentially add other fields from record['extra'] if needed later
    }
