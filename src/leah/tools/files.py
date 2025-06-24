from datetime import datetime
import json
import os
import traceback
from typing import Any, Dict, List

import requests
from leah.actions.IActions import IAction
from leah.utils.GlobalFileManager import GlobalFileManager
from langchain_core.tools import tool
from leah.config.LocalConfigManager import LocalConfigManager

def get_file_manager():
    return GlobalFileManager(LocalConfigManager("default"), "/", "/")

@tool
def get_absolute_path_of_file(file_path: str):
    """
    Get the absolute path of a file.
    """
    file_manager = get_file_manager()
    abs_path = file_manager.get_absolute_path(file_path)
    return f"The absolute path of {file_path} is {abs_path}"

@tool
def read_file(file_path: str):
    """
    Read the contents of a file.
    """
    file_manager = get_file_manager()
    if not file_path:
        return "File path is required"
    
    if file_path.endswith(".note"):
        return "This is a note, please use the notes action to read it."

    # Check file size before reading
    try:
        if not os.path.exists(file_path):
            return f"File {file_path} not found"
        if not os.path.isfile(file_path):
            return f"Path {file_path} is not a file."
        size = os.path.getsize(file_path)
        if size > 65536:
            return f"File {file_path} is too long to read (size: {size} bytes). Please use read_file_partial instead."
    except Exception as e:
        return f"Error checking file size: {str(e)}"

    try:
        content = file_manager.get_file(file_path)
        if content is None:
            return f"File {file_path} not found"
        else:
            return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def list_files(file_path: str):
    """
    List all files in a directory.
    """
    file_manager = get_file_manager()
    if not file_path:
        return "File path is required"
    files = file_manager.list_files_recusive(file_path)
    return "I listed the files in " + file_path + " and here are the results: " + str("\n".join(files))

@tool
def get_file_info(file_path: str):
    """
    Get information about a file.
    """
    file_manager = get_file_manager()
    if not file_path:
        return "File path is required"
    try:
        info = file_manager.get_file_info(file_path)
        if info is None:
            return f"File {file_path} not found"
        else:
            info = json.dumps(info, indent=4)
            return f"File info for {file_path}: {info}"
    except Exception as e:
        return f"Error getting file info: {str(e)}"

@tool
def search_files(search_terms: List[str], path: str, case_sensitive: bool):
    """
    Search for files and directories containing specified search terms in their names.
    """
    if not search_terms:
        return "At least one search term is required"
    if not path:
        return "Path is required"
    if not case_sensitive:
        return "Case sensitive is required"
    
    search_terms = [term.strip() for term in search_terms if term.strip()]

    if not search_terms:
        return "At least one valid search term is required"
    
    try:
        matches = GlobalFileManager().search_files(search_terms, path, case_sensitive)
        if matches:
            return f"Found {len(matches)} matching files/directories:\n" + "\n".join(matches)
        else:
            return "No files or directories found matching the search terms."
    except Exception as e:
        return f"Error searching files: {str(e)}"

@tool
def search_files_containing(search_term: List[str], path: str, case_sensitive: bool):
    """
    Search for files containing the specified search term in their content (similar to grep).
    """

    if not search_term:
        return "Search term is required"

    try:
        matches = GlobalFileManager().content_search(search_term, path, case_sensitive)
        if matches:
            return f"Found matches in files:\n" + "\n".join(matches)
        else:
            return "No files found containing the search term."
    except Exception as e:
        return f"Error searching file contents: {str(e)}"

@tool
def create_file(file_path: str):
    """
    Create a new empty file.
    """
    file_path = os.path.abspath(file_path)
    file_manager = get_file_manager()
    file_manager.put_file(file_path, b"")
    return f"I have created a file at {file_path}"

@tool
def edit_file(file_path: str, offset: int, delete_chars: int, insert_chars: str):
    """
    Edit a file by replacing a part of the file with a new string.
    The offset is the position to start the edit.
    The delete_chars is the number of characters to delete.
    The insert_chars is the string to insert.
    """
    try:    
        file_manager = get_file_manager()
        file_manager.edit_file(file_path, offset, delete_chars, insert_chars)
        return f"I have edited the file {file_path}"
    except Exception as e:
        return f"I received the following error: {str(e)}"

@tool
def append_file_lines(file_path: str, append_lines: List[str]):
    """
    Append lines to a file.
    """
    try:
        file_manager = get_file_manager()
        file_manager.append_file_lines(file_path, append_lines)
        return f"I have appended the lines {append_lines} to the file {file_path}"
    except Exception as e:
        return f"I received the following error: {str(e)}"

@tool
def insert_file_lines(file_path: str, line_number: int, insert_lines: List[str]):
    """
    Edit a file by inserting a line.
    The line_number is the line insert under.
    The insert_line is the line to insert.
    """
    if not file_path:
        return "File path is required"
    if not line_number:
        return "Line number is required"
    if not insert_lines:
        return "Insert lines is required"

    try:
        file_manager = get_file_manager()
        file_manager.insert_file_lines(file_path, line_number, insert_lines)
        return f"I have inserted the lines {insert_lines} under the line {line_number} in the file {file_path}"
    except Exception as e:
        print(e)
        traceback.print_exc()
        return f"I received the following error: {str(e)}"

@tool
def replace_file_lines(file_path: str, start_line_number: int, end_line_number: int, replace_lines: List[str] ):
    """
    Replace a line in a file.
    The start_line_number is the line to replace from.
    The end_line_number is the line to replace to.
    The replace_lines is the lines to replace with.
    """
    if not file_path:
        return "File path is required"
    if not start_line_number:
        return "Start line number is required"
    if not end_line_number:
        return "End line number is required"
    if not replace_lines:
        return "Replace lines is required"
    
    try:
        file_manager = get_file_manager()
        file_manager.replace_file_lines(file_path, start_line_number, end_line_number, replace_lines)
        return f"I have replaced the lines {start_line_number} to {end_line_number} with {replace_lines} in the file {file_path}"
    except Exception as e:
        return f"I received the following error: {str(e)}"

@tool
def delete_file_lines(file_path: str, start_line_number: int, end_line_number: int):
    """
    Delete lines from a file.
    """
    try:
        file_manager = get_file_manager()
        file_manager.delete_file_lines(file_path, start_line_number, end_line_number)
        return f"I have deleted the lines {start_line_number} to {end_line_number} from the file {file_path}"
    except Exception as e:
        return f"I received the following error: {str(e)}"

@tool
def read_file_lines(file_path: str, start_line_number: int = 1, end_line_number: int = None):
    """
    Get the lines of a file.
    The optional start_line_number is the line to start from.
    The optional end_line_number is the line to end at.
    If end_line_number is not provided, all lines are returned.
    """
    file_manager = get_file_manager()
    lines = file_manager.get_file_lines(file_path, start_line_number, end_line_number)
    return "I read the lines of the file " + file_path + " and here are the results: " + str("\n".join(lines))

@tool
def search_file_lines(file_path: str, search_term: str):
    """
    Search for a term in a file. Will show the line number and the line.
    """
    file_manager = get_file_manager()
    lines = file_manager.get_file_lines(file_path)
    matches = []
    for line in lines:  
        if search_term in line:
            matches.append(line)
    if matches:
        return "Search term found on the following lines:\n" + "\n".join(matches)
    else:
        return "I did not find the term " + search_term + " in the file " + file_path


@tool
def copy_file(source_path: str, target_path: str):
    """
    Copy a file to a new location.
    """
    file_manager = get_file_manager()
    file_manager.copy_file(source_path, target_path)
    return f"I have copied a file from {source_path} to {target_path}"

@tool
def move_file(source_path: str, target_path: str):
    """
    Move a file to a new location.
    """
    if not source_path or not target_path:
        return "Source path and target path are required"
    
    file_manager = get_file_manager()
    
    try:
        actual_path = file_manager.move_file(source_path, target_path)
        return f"I have moved a file from {source_path} to {actual_path}"
    except FileNotFoundError:
        return f"I attempted to move a file from {source_path} to {target_path} but the source file was not found"
    except Exception as e:
        return f"I attempted to move a file from {source_path} to {target_path} but received the following error: {str(e)}"

@tool
def delete_file(file_path: str):
    """
    Delete a file from the file system.
    """
    if not file_path:
        return "File path is required"
    
    file_manager = get_file_manager()
    
    try:
        if file_manager.delete_file(file_path):
            return f"I have deleted a file from {file_path} (moved to backup)"
        else:
            return f"I attempted to delete a file from {file_path} but it was not found"
    except Exception as e:
        return f"I attempted to delete a file from {file_path} but received the following error: {str(e)}"

@tool
def download_file(url: str, file_path: str):
    """
    Download a file from a URL and save it to the file system.
    """
    if not url or not file_path:
        return "URL and file path are required"
    
    try:
        response = requests.get(url, stream=True)
        try:
            response.raise_for_status()
        except Exception as e:
            return f"I attempted to download the file from {url} but received the following error: {str(e)}"
        content = response.content
        full_path = os.path.abspath(get_file_manager().put_file(file_path, content))
        return f"I have downloaded the file from {url} and saved it to {full_path}"
    except Exception as e:
        return f"I attempted to download the file from {url} but received the following error: {str(e)}"

@tool
def read_file_partial(file_path: str, offset: int, length: int):
    """
    Read a specific number of characters from a file, starting at the given offset. The maximum read size is 8192 characters.
    The result starts with a single line indicating the offset and number of characters read.
    """
    file_manager = get_file_manager()
    if not file_path:
        return "File path is required"
    if offset < 0 or length <= 0:
        return "Offset must be >= 0 and length must be > 0"
    max_read_size = 8192
    read_length = min(length, max_read_size)
    try:
        content = file_manager.get_file(file_path)
        if content is None:
            return f"File {file_path} not found"
        if not isinstance(content, str):
            content = content.decode('utf-8')
        end = offset + read_length
        partial_content = content[offset:end]
        actual_read = len(partial_content)
        header = f"Read {actual_read} characters from offset {offset}:"
        return f"{header}\n{partial_content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

