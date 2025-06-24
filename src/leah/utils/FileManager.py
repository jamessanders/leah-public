import os
import shutil
from datetime import datetime
from typing import Optional, List, Tuple

class FileManager:
    def __init__(self, config_manager):
        """
        Initialize the FileManager with a LocalConfigManager instance.
        
        Args:
            config_manager (LocalConfigManager): The LocalConfigManager instance to use for path management
        """
        self.config_manager = config_manager
        self.files_directory = self.config_manager.get_persona_path("files")
        if not os.path.exists(self.files_directory):
            os.makedirs(self.files_directory, exist_ok=True)
        # Create backup directory within files directory
        self.backup_directory = os.path.join(self.files_directory, "backup")
        if not os.path.exists(self.backup_directory):
            os.makedirs(self.backup_directory, exist_ok=True)

    def _sanitize_path(self, file_path: str) -> tuple[str, str]:
        """
        Process a file path to ensure it's safe and get both directory and filename.
        Handles both absolute and relative paths.
        
        Args:
            file_path (str): The full file path or filename
            
        Returns:
            tuple[str, str]: (relative_directory_path, filename)
            relative_directory_path is empty string if no directory specified
        """
        # Normalize the path (resolve .. and . components)
        normalized = os.path.normpath(file_path)
        
        # Split into directory and filename
        directory, filename = os.path.split(normalized)
        
        # Remove any initial / or drive letter (e.g., C:)
        directory = os.path.normpath(directory.lstrip(os.path.sep))
        if os.path.splitdrive(directory)[1]:
            directory = os.path.splitdrive(directory)[1].lstrip(os.path.sep)
            
        # Replace backslashes with forward slashes for consistency
        directory = directory.replace('\\', '/')
        
        # Remove any attempts to traverse up
        directory = '/'.join(part for part in directory.split('/') 
                           if part and part != '..' and part != '.')
        
        return directory, filename

    def _ensure_directory_exists(self, relative_dir: str) -> None:
        """
        Ensure the specified directory exists under files_directory.
        Creates it if it doesn't exist.
        
        Args:
            relative_dir (str): Relative directory path
        """
        if relative_dir:
            full_dir = os.path.join(self.files_directory, relative_dir)
            os.makedirs(full_dir, exist_ok=True)

    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Retrieve the content of a specific file in binary mode.
        Can accept either a filename or a full path - will always look relative to files_directory.
        
        Args:
            file_path (str): Name of the file or full path to retrieve
            
        Returns:
            Optional[bytes]: The file contents as bytes if file exists, None otherwise
        """
        rel_dir, filename = self._sanitize_path(file_path)
        target_path = os.path.join(self.files_directory, rel_dir, filename)
        
        if os.path.exists(target_path):
            with open(target_path, 'rb') as file:
                return file.read()
        return None

    def put_file(self, file_path: str, content: bytes) -> str:
        """
        Store binary content into a specific file.
        Can accept either a filename or a full path - will always store relative to files_directory.
        Creates directories as needed.
        
        Args:
            file_path (str): Name of the file or full path to store
            content (bytes): Binary content to store in the file
            
        Returns:
            str: The actual path where the file was stored
        """
        rel_dir, filename = self._sanitize_path(file_path)
        self._ensure_directory_exists(rel_dir)
        
        target_path = os.path.abspath(os.path.join(self.files_directory, rel_dir, filename))
        
        # Create backup if file exists
        if os.path.exists(target_path):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            name, ext = os.path.splitext(filename)
            backup_name = f"{name}_{timestamp}{ext}"
            # Maintain same directory structure in backup
            backup_dir = os.path.join(self.backup_directory, rel_dir)
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(target_path, backup_path)
        
        if isinstance(content, str):
            content = content.encode('utf-8')

        with open(target_path, 'wb') as file:
            file.write(content)
            
        return target_path

    def get_all_files(self, path: str = "") -> List[str]:
        """
        Retrieve the relative paths of all files in the directory and its subdirectories,
        excluding files in the backup directory.
        
        Returns:
            List[str]: List of all file paths relative to files_directory, excluding backup files
        """
        files = []
        backup_rel_path = os.path.relpath(self.backup_directory, self.files_directory)
        for root, _, filenames in os.walk(os.path.join(self.files_directory, path)):
            # Skip the backup directory
            if os.path.relpath(root, self.files_directory).startswith(backup_rel_path):
                continue
                
            rel_root = os.path.relpath(root, self.files_directory)
            for filename in filenames:
                if rel_root == '.':
                    files.append(filename)
                else:
                    files.append(os.path.join(rel_root, filename))
        return files

    def get_files_by_size(self, path: str = "", max_files: Optional[int] = None) -> List[str]:
        """
        Retrieve the relative paths of all files ordered by size from largest to smallest,
        excluding files in the backup directory.
        
        Args:
            max_files (Optional[int]): Maximum number of files to return
            
        Returns:
            List[str]: List of file paths relative to files_directory ordered by size, excluding backup files
        """
        files_with_size = []
        backup_rel_path = os.path.relpath(self.backup_directory, self.files_directory)
        for root, _, filenames in os.walk(os.path.join(self.files_directory, path)):
            # Skip the backup directory
            if os.path.relpath(root, self.files_directory).startswith(backup_rel_path):
                continue
                
            rel_root = os.path.relpath(root, self.files_directory)
            for filename in filenames:
                rel_path = os.path.join(rel_root, filename).replace('\\', '/')
                if rel_root == '.':
                    rel_path = filename
                full_path = os.path.join(root, filename)
                files_with_size.append((rel_path, os.path.getsize(full_path)))
                
        # Sort files by size in descending order
        files_with_size.sort(key=lambda x: x[1], reverse=True)
        return [file[0] for file in files_with_size[:max_files]]

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get metadata about a specific file.
        
        Args:
            file_path (str): Path to the file relative to files_directory
            
        Returns:
            Optional[dict]: Dictionary containing file metadata if file exists
        """
        rel_dir, filename = self._sanitize_path(file_path)
        target_path = os.path.join(self.files_directory, rel_dir, filename)
        
        if os.path.exists(target_path):
            stats = os.stat(target_path)
            return {
                'size': stats.st_size,
                'created': datetime.fromtimestamp(stats.st_ctime),
                'modified': datetime.fromtimestamp(stats.st_mtime),
                'accessed': datetime.fromtimestamp(stats.st_atime),
                'relative_path': os.path.join(rel_dir, filename).replace('\\', '/')
            }
        return None

    def move_file(self, source_path: str, target_path: str) -> str:
        """
        Move a file from source path to target path.
        Creates backup of target file if it exists.
        Creates necessary directories in the target path.
        
        Args:
            source_path (str): Source file path relative to files_directory
            target_path (str): Target file path relative to files_directory
            
        Returns:
            str: The actual path where the file was moved to
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If there's an error during the move operation
        """
        source_dir, source_filename = self._sanitize_path(source_path)
        target_dir, target_filename = self._sanitize_path(target_path)
        
        source_full_path = os.path.join(self.files_directory, source_dir, source_filename)
        target_full_path = os.path.join(self.files_directory, target_dir, target_filename)
        
        if not os.path.exists(source_full_path):
            raise FileNotFoundError(f"Source file {source_path} not found")
            
        # Create target directory if needed
        self._ensure_directory_exists(target_dir)
        
        # Create backup if target exists
        if os.path.exists(target_full_path):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            name, ext = os.path.splitext(target_filename)
            backup_name = f"{name}_{timestamp}{ext}"
            backup_dir = os.path.join(self.backup_directory, target_dir)
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(target_full_path, backup_path)
        
        # Move the file
        shutil.move(source_full_path, target_full_path)
        return target_full_path

    def get_absolute_path(self, file_path) -> str:
        # Normalize the path (resolve .. and . components)
        normalized = os.path.normpath(file_path)
        
        # Split into directory and filename
        directory, filename = os.path.split(normalized)
        source_path = os.path.join(self.files_directory, directory, filename)
        return os.path.abspath(source_path)

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file, moving it to a backup directory instead of permanent deletion.
        
        Args:
            file_path (str): Path of file to delete relative to files_directory
            
        Returns:
            bool: True if file was deleted (moved to backup), False if file didn't exist
        """
        rel_dir, filename = self._sanitize_path(file_path)
        source_path = os.path.join(self.files_directory, rel_dir, filename)
        
        if not os.path.exists(source_path):
            return False
            
        # Move to backup instead of deleting
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        name, ext = os.path.splitext(filename)
        backup_name = f"{name}_{timestamp}_deleted{ext}"
        backup_dir = os.path.join(self.backup_directory, rel_dir)
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, backup_name)
        
        shutil.move(source_path, backup_path)
        return True 