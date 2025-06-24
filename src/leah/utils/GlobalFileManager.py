import os
import shutil
from datetime import datetime
from typing import Optional, List
import io
import sys
import tempfile
try:
    import patch
except ImportError:
    raise ImportError("The 'patch' library is required for applying diffs. Install it with 'pip install patch'.")

class GlobalFileManager:
    def __init__(self, config_manager, read_root: str, write_root: str):
        """
        Initialize the GlobalFileManager with read and write roots.
        
        Args:
            config_manager (LocalConfigManager): The LocalConfigManager instance to use for path management
            read_root (str): The root directory for reading files
            write_root (str): The root directory for writing files
        """
        self.config_manager = config_manager
        self.read_root = os.path.abspath(read_root)
        self.write_root = os.path.abspath(write_root)

        if not os.path.exists(self.read_root):
            os.makedirs(self.read_root, exist_ok=True)
        if not os.path.exists(self.write_root):
            os.makedirs(self.write_root, exist_ok=True)

    def _is_within_root(self, path: str, root: str) -> bool:
        """
        Check if a given path is within a specified root directory.
        
        Args:
            path (str): The path to check
            root (str): The root directory
        
        Returns:
            bool: True if path is within root, False otherwise
        """
        abs_path = os.path.abspath(path)
        return abs_path.startswith(root)

    def get_file_lines(self, file_path: str, start_line_number: int = 1, end_line_number: int = None) -> List[str]:
        """
        Get the lines of a file.
        The lines are padded with a line number (padded with whitespace to equal width) and a colon.
        The start_line_number is the line to start from.
        The end_line_number is the line to end at.
        If end_line_number is not provided, all lines are returned.
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()

        if end_line_number is None:
            end_line_number = len(lines)

        lines = lines[start_line_number-1:end_line_number]

        width = len(str(len(lines)))
        def pad(n: int) -> str:
            # return n padded with spaces to the width of the largest line number
            return str(n).rjust(width)

        return [pad(n+1) + ": " + line for n, line in enumerate(lines)]

    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Retrieve the content of a specific file in binary mode, only if within read_root.
        Handles both relative and absolute paths.
        
        Args:
            file_path (str): Name of the file or full path to retrieve
            
        Returns:
            Optional[bytes]: The file contents as bytes if file exists, None otherwise
        """
        # Determine if the file_path is absolute or relative
        if os.path.isabs(file_path):
            full_path = file_path
        else:
            full_path = os.path.join(self.read_root, file_path)

        if not self._is_within_root(full_path, self.read_root):
            raise PermissionError("Read operation not allowed outside read_root")
        if os.path.exists(full_path):
            with open(full_path, 'rb') as file:
                return file.read()
        return None

    def put_file(self, file_path: str, content: bytes) -> str:
        """
        Store binary content into a specific file, only if within write_root.
        Handles both relative and absolute paths.
        
        Args:
            file_path (str): Name of the file or full path to store
            content (bytes): Binary content to store in the file
            
        Returns:
            str: The actual path where the file was stored
        """
        # Determine if the file_path is absolute or relative
        if os.path.isabs(file_path):
            full_path = file_path
        else:
            full_path = os.path.abspath(os.path.join(self.write_root, file_path))

        if not self._is_within_root(full_path, self.write_root):
            raise PermissionError(f"Write operation not allowed outside of your root directoy of {self.write_root}")
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as file:
            file.write(content)
        return os.path.abspath(full_path)

    def list_files(self, path: str = "") -> List[str]:
        """
        List files and directories in the specified directory if they are under the read_root, returning absolute paths.
        This method does not recurse into subdirectories.
        Handles both relative and absolute paths.
        
        Args:
            path (str): Path to list files from, can be relative or absolute
        
        Returns:
            List[str]: List of absolute file paths
        """
        # Determine if the path is absolute or relative
        if os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.abspath(os.path.join(self.read_root, path))

        if not self._is_within_root(full_path, self.read_root):
            raise PermissionError("Listing files not allowed outside read_root")
        
        # List files and directories in the directory without recursion
        files = []
        if os.path.isdir(full_path):
            for filename in os.listdir(full_path):
                file_path = os.path.abspath(os.path.join(full_path, filename))
                files.append(file_path)
        return files

    def list_files_recusive(self, path: str = "") -> List[str]:
        """
        List files and directories in the specified directory if they are under the read_root, returning absolute paths.
        Handles both relative and absolute paths.
        
        Args:
            path (str): Path to list files from, can be relative or absolute
        
        Returns:
            List[str]: List of absolute file and directory paths with labels
        """
        # Determine if the path is absolute or relative
        if os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(self.read_root, path)

        if not self._is_within_root(full_path, self.read_root):
            raise PermissionError("Listing files not allowed outside read_root")
        files = []
        for root, _, filenames in os.walk(full_path):
            for filename in filenames:
                files.append(f"File: {os.path.abspath(os.path.join(root, filename))}")
            for dirname in os.listdir(root):
                dir_path = os.path.join(root, dirname)
                if os.path.isdir(dir_path):
                    files.append(f"Directory: {os.path.abspath(os.path.join(root, dirname))}")
        return files

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get metadata about a specific file, including size, last modified, and created time.
        Handles both relative and absolute paths.
        
        Args:
            file_path (str): Path to the file relative to read_root
            
        Returns:
            Optional[dict]: Dictionary containing file metadata if file exists
        """
        # Determine if the file_path is absolute or relative
        if os.path.isabs(file_path):
            full_path = file_path
        else:
            full_path = os.path.join(self.read_root, file_path)

        if not self._is_within_root(full_path, self.read_root):
            raise PermissionError("Operation not allowed outside read_root")
        if os.path.exists(full_path):
            stats = os.stat(full_path)
            return {
                'size': stats.st_size,
                'created': datetime.fromtimestamp(stats.st_ctime),
                'modified': datetime.fromtimestamp(stats.st_mtime),
                'accessed': datetime.fromtimestamp(stats.st_atime),
                'absolute_path': full_path
            }
        return None

    def get_absolute_path(self, file_path: str) -> str:
        """
        Get the absolute path for a file within the read_root.

        Args:
            file_path (str): Path to the file, can be relative or absolute

        Returns:
            str: The absolute path to the file
        """
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.read_root, file_path)

    def copy_file(self, source_path: str, target_path: str) -> str:
        """
        Copy a file from source path to target path within the write_root.
        """
        if not os.path.isabs(source_path):
            source_path = os.path.join(self.write_root, source_path)
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.write_root, target_path)
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file {source_path} not found")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copy(source_path, target_path)
        return target_path

    def move_file(self, source_path: str, target_path: str) -> str:
        """
        Move a file from source path to target path within the write_root.
        Creates necessary directories in the target path.

        Args:
            source_path (str): Source file path, can be relative or absolute
            target_path (str): Target file path, can be relative or absolute

        Returns:
            str: The actual path where the file was moved to

        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If there's an error during the move operation
        """
        if not os.path.isabs(source_path):
            source_path = os.path.join(self.write_root, source_path)
        if not os.path.isabs(target_path):
            target_path = os.path.join(self.write_root, target_path)

        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file {source_path} not found")

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.move(source_path, target_path)
        return target_path

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from the write_root, moving it to a .backup directory with a timestamp before deletion.

        Args:
            file_path (str): Path of file to delete, can be relative or absolute

        Returns:
            bool: True if file was deleted (moved to backup), False if file didn't exist
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.write_root, file_path)

        if os.path.exists(file_path):
            # Create backup directory
            backup_dir = os.path.join(os.path.dirname(file_path), '.backup')
            os.makedirs(backup_dir, exist_ok=True)

            # Create backup file name with timestamp
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_file_name = f"{os.path.basename(file_path)}_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_file_name)

            # Move file to backup
            shutil.move(file_path, backup_path)
            return True
        return False

    def edit_file(self, file_path: str, offset: int, delete_chars: int, insert_chars: str):
        """
        Edit a file using a patch.
        The offset is the position to start the edit.
        The delete_chars is the number of characters to delete.
        The insert_chars is the string to insert.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.write_root, file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
        new_content = content[:offset] + insert_chars + content[offset + delete_chars:]
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)

    def replace_file_lines(self, file_path: str, start_line_number: int, end_line_number: int, replacement_lines: List[str]):
        """
        Replace a line in a file.
        The line_number is the line to replace.
        The replace_line is the line to replace with.
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            lines = [line.rstrip('\n') for line in file.readlines()]

        if end_line_number >= len(lines):
            # add empty lines till we reach the line_number
            lines.extend([""] * (end_line_number - len(lines)))

        # delete the lines between start_line_number and end_line_number (inclusive, 1-based)
        lines = lines[0:start_line_number-1] + replacement_lines + lines[end_line_number:]
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("\n".join(lines))
        return f"I have replaced the lines {start_line_number} to {end_line_number} with {replacement_lines} in the file {file_path}"

    def append_file_lines(self, file_path: str, append_lines: List[str]):
        """
        Append lines to a file.
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            lines = [line.rstrip('\n') for line in file.readlines()]
        lines.extend(append_lines)
    
    def insert_file_lines(self, file_path: str, line_number: int, insert_lines: List[str]):
        """
        Insert lines before the original line at the given line_number (1-based).
        The line_number is the line to insert under (i.e., before the original line N).
        The insert_lines are the lines to insert.
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            lines = [line.rstrip('\n') for line in file.readlines()]
        if len(lines) == 0:
            lines = [""]

        if line_number > len(lines):
            # add empty lines till we reach the line_number
            lines.extend([""] * (line_number - len(lines)))

        # insert the lines after the original line at line_number
        lines = lines[0:line_number] + insert_lines + lines[line_number:]
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write("\n".join(lines))
        return f"I have inserted the lines {insert_lines} under the line {line_number} in the file {file_path}"
    
    def delete_file_lines(self, file_path: str, start_line_number: int, end_line_number: int):
        """
        Delete lines from a file. Line numbers are 1-based and inclusive.
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            lines = file.readlines()
        # Convert to 0-based indices, and end_line_number is inclusive
        del lines[start_line_number-1:end_line_number]
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(lines)

    def search_files(self, search_strings: List[str], path: str = "", case_sensitive: bool = False) -> List[str]:
        """
        Recursively search for files containing any of the search strings in their name.
        
        Args:
            search_strings (List[str]): List of strings to search for in file names
            path (str): Starting path for the search, can be relative or absolute
            case_sensitive (bool): Whether the search should be case-sensitive
            
        Returns:
            List[str]: List of absolute paths to files that match any of the search criteria
            
        Raises:
            PermissionError: If the search path is outside read_root
            ValueError: If search_strings is empty
        """
        if not search_strings:
            raise ValueError("At least one search string must be provided")

        # Determine if the path is absolute or relative
        if os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(self.read_root, path)

        if not self._is_within_root(full_path, self.read_root):
            raise PermissionError("Search operation not allowed outside read_root")

        matches = set()  # Using set to avoid duplicates
        
        # If case-insensitive search is requested, convert search strings to lowercase
        if not case_sensitive:
            search_strings = [s.lower() for s in search_strings]

        # Walk through directory tree
        for root, dirs, files in os.walk(full_path):
            # Search in file names
            for filename in files:
                # Apply case sensitivity setting
                compare_name = filename if case_sensitive else filename.lower()
                # Check if any search string matches
                if any(search_string in compare_name for search_string in search_strings):
                    matches.add(os.path.abspath(os.path.join(root, filename)))
            
            # Search in directory names
            for dirname in dirs:
                # Apply case sensitivity setting
                compare_name = dirname if case_sensitive else dirname.lower()
                # Check if any search string matches
                if any(search_string in compare_name for search_string in search_strings):
                    matches.add(os.path.abspath(os.path.join(root, dirname)))

        return sorted(list(matches))  # Convert set back to sorted list

    def content_search(self, search_term: str, path: str = "", case_sensitive: bool = False) -> List[str]:
        """
        Search for a term within all text files in the specified directory and its subdirectories.
        Only searches within the read_root directory. Returns results in grep-like format.
        
        Args:
            search_term (str): The term to search for in the files
            path (str): The path within read_root to start the search (default: root)
            case_sensitive (bool): Whether the search should be case-sensitive (default: False)
            
        Returns:
            List[str]: List of strings in format "absolute_path:line_number:matching_line"
            
        Raises:
            PermissionError: If the search path is outside read_root
        """
        # Determine if the path is absolute or relative
        if os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(self.read_root, path)

        if not self._is_within_root(full_path, self.read_root):
            raise PermissionError("Content search operation not allowed outside read_root")

        results = []
        
        for root, _, filenames in os.walk(full_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                
                try:
                    # Try to open and read the file as text
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                        for line_num, line in enumerate(file, 1):
                            if case_sensitive:
                                if search_term in line:
                                    results.append(f"{file_path}:{line_num}:{line.strip()}")
                            else:
                                if search_term.lower() in line.lower():
                                    results.append(f"{file_path}:{line_num}:{line.strip()}")
                except (UnicodeDecodeError, IOError):
                    # Skip files that can't be read as text
                    continue
                    
        return results 