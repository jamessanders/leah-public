import os
from langchain_core.tools import tool

@tool
def get_file_extension(file_path: str) -> str:
    """Returns the extension of a file.
    For example, get_file_extension('document.txt') returns '.txt'
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    if not os.path.isfile(file_path):
        return f"Error: Path {file_path} is not a file."
    _, extension = os.path.splitext(file_path)
    return extension

@tool
def get_file_name(file_path: str) -> str:
    """Returns the name of a file without the extension.
    For example, get_file_name('/path/to/document.txt') returns 'document'
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    if not os.path.isfile(file_path):
        return f"Error: Path {file_path} is not a file."
    base_name = os.path.basename(file_path)
    file_name, _ = os.path.splitext(base_name)
    return file_name

@tool
def count_characters(text: str) -> int:
    """Counts the number of characters in a string, including spaces."""
    return len(text)
