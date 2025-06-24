from langchain_core.tools import tool
import os
import shutil

@tool
def get_current_directory() -> str:
    """Returns the current working directory."""
    return os.getcwd()

@tool
def create_directory(path: str) -> str:
    """Creates a directory at the specified path.
    Returns a success message or an error message.
    """
    try:
        os.makedirs(path, exist_ok=True)
        return f"Successfully created directory: {path}"
    except Exception as e:
        return f"Error creating directory {path}: {e}"

@tool
def path_exists(path: str) -> bool:
    """Checks if a file or directory exists at the specified path."""
    return os.path.exists(path)

@tool
def get_file_size(file_path: str) -> str:
    """Returns the size of a file in bytes.
    Returns the size or an error message.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    if not os.path.isfile(file_path):
        return f"Error: Path {file_path} is a directory, not a file."
    try:
        size = os.path.getsize(file_path)
        return f"File size: {size} bytes"
    except Exception as e:
        return f"Error getting file size for {file_path}: {e}"

@tool
def reverse_string(text: str) -> str:
    """Reverses the given string."""
    return text[::-1]
