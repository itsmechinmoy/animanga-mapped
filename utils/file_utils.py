"""
File I/O utilities
File: utils/file_utils.py
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Union

def load_json(filepath: Union[str, Path]) -> Any:
    """
    Load JSON file
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath: Union[str, Path], data: Any, pretty: bool = False):
    """
    Save data to JSON file
    
    Args:
        filepath: Path to save JSON file
        data: Data to serialize
        pretty: Whether to pretty-print the JSON (default: False)
    """
    filepath = Path(filepath)
    
    # Create parent directories if they don't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)

def file_exists(filepath: Union[str, Path]) -> bool:
    """
    Check if file exists
    
    Args:
        filepath: Path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return Path(filepath).exists()

def get_file_age(filepath: Union[str, Path]) -> float:
    """
    Get file age in seconds
    
    Args:
        filepath: Path to file
        
    Returns:
        Age of file in seconds
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    import time
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    return time.time() - filepath.stat().st_mtime

def ensure_directory(dirpath: Union[str, Path]):
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        dirpath: Directory path
    """
    Path(dirpath).mkdir(parents=True, exist_ok=True)
