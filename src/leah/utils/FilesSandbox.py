import os
from typing import Optional, List, Tuple
from leah.utils.FileManager import FileManager

class FilesSandbox:
    def __init__(self, file_manager: FileManager, sandbox_path: str):
        """
        Initialize the FilesSandbox with a FileManager instance and sandbox path.
        
        Args:
            file_manager (FileManager): The FileManager instance to wrap
            sandbox_path (str): The relative path under which all operations will be sandboxed
        """
        self.file_manager = file_manager
        # Sanitize and normalize the sandbox path
        self.sandbox_path = os.path.normpath(sandbox_path.strip('/')).replace('\\', '/')
        
    def _add_sandbox_path(self, file_path: str) -> str:
        """
        Add sandbox path to the given file path.
        
        Args:
            file_path (str): Original file path
            
        Returns:
            str: File path with sandbox prefix
        """
        # Normalize the path and remove any leading/trailing slashes
        normalized = os.path.normpath(file_path.strip('/')).replace('\\', '/')
        return os.path.join(self.sandbox_path, normalized).replace('\\', '/')
        
    def _remove_sandbox_path(self, file_path: str) -> str:
        """
        Remove sandbox path prefix from the given file path.
        
        Args:
            file_path (str): File path with sandbox prefix
            
        Returns:
            str: Original file path without sandbox prefix
        """
        if file_path.startswith(self.sandbox_path):
            return file_path[len(self.sandbox_path):].strip('/').strip("\\")
        return file_path.strip('/').strip("\\")

    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Retrieve the content of a specific file in binary mode from the sandbox.
        
        Args:
            file_path (str): Name of the file or path relative to sandbox
            
        Returns:
            Optional[bytes]: The file contents as bytes if file exists, None otherwise
        """
        sandboxed_path = self._add_sandbox_path(file_path)
        return self.file_manager.get_file(sandboxed_path)

    def put_file(self, file_path: str, content: bytes) -> str:
        """
        Store binary content into a specific file in the sandbox.
        
        Args:
            file_path (str): Name of the file or path relative to sandbox
            content (bytes): Binary content to store in the file
            
        Returns:
            str: The path where the file was stored, relative to sandbox
        """
        sandboxed_path = self._add_sandbox_path(file_path)
        actual_path = self.file_manager.put_file(sandboxed_path, content)
        return self._remove_sandbox_path(os.path.relpath(actual_path, self.file_manager.files_directory))

    def get_all_files(self, path: str = "") -> List[str]:
        """
        Retrieve all files in the sandbox directory and its subdirectories.
        
        Args:
            path (str): Additional path within sandbox to list
            
        Returns:
            List[str]: List of all file paths relative to sandbox
        """
        sandboxed_path = self._add_sandbox_path(path)
        files = self.file_manager.get_all_files(sandboxed_path)
        return [self._remove_sandbox_path(f) for f in files if f.startswith(self.sandbox_path)]

    def get_files_by_size(self, path: str = "", max_files: Optional[int] = None) -> List[str]:
        """
        Retrieve files ordered by size from largest to smallest within the sandbox.
        
        Args:
            path (str): Additional path within sandbox to list
            max_files (Optional[int]): Maximum number of files to return
            
        Returns:
            List[str]: List of file paths relative to sandbox ordered by size
        """
        sandboxed_path = self._add_sandbox_path(path)
        files = self.file_manager.get_files_by_size(sandboxed_path, max_files)
        return [self._remove_sandbox_path(f) for f in files if f.startswith(self.sandbox_path)]

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get metadata about a specific file in the sandbox.
        
        Args:
            file_path (str): Path to the file relative to sandbox
            
        Returns:
            Optional[dict]: Dictionary containing file metadata if file exists
        """
        sandboxed_path = self._add_sandbox_path(file_path)
        info = self.file_manager.get_file_info(sandboxed_path)
        if info and 'relative_path' in info:
            info['relative_path'] = self._remove_sandbox_path(info['relative_path'])
        return info

    def move_file(self, source_path: str, target_path: str) -> str:
        """
        Move a file within the sandbox.
        
        Args:
            source_path (str): Source file path relative to sandbox
            target_path (str): Target file path relative to sandbox
            
        Returns:
            str: The path where the file was moved to, relative to sandbox
        """
        sandboxed_source = self._add_sandbox_path(source_path)
        sandboxed_target = self._add_sandbox_path(target_path)
        actual_path = self.file_manager.move_file(sandboxed_source, sandboxed_target)
        return self._remove_sandbox_path(os.path.relpath(actual_path, self.file_manager.files_directory))

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from the sandbox.
        
        Args:
            file_path (str): Path of file to delete relative to sandbox
            
        Returns:
            bool: True if file was deleted, False if file didn't exist
        """
        sandboxed_path = self._add_sandbox_path(file_path)
        return self.file_manager.delete_file(sandboxed_path)


    def get_absolute_path(self, file_path: str) -> str:
        """
        Get the absolute path for a file in the sandbox.
        
        Args:
            file_path (str): Path to the file relative to sandbox
            
        Returns:
            str: The absolute path to the file in the filesystem
        """
        sandboxed_path = self._add_sandbox_path(file_path)
        return self.file_manager.get_absolute_path(sandboxed_path) 