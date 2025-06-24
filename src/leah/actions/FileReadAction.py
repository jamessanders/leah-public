from datetime import datetime
import json
from typing import Any, Dict, List
from leah.actions.IActions import IAction
from leah.utils.GlobalFileManager import GlobalFileManager

class FileReadAction(IAction): 
    def __init__(self, config_manager, persona, query, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.file_manager = GlobalFileManager(config_manager, '/', config_manager.get_persona_path(self.persona))

    def getTools(self):
        return [
            (self.get_file,
             "get_file", 
             "Read the contents of a file. The file path can include subdirectories.", 
             {"file_path": "<the path of the file to read>"}),
            (self.get_absolute_path,"get_absolute_path", "get the absolute path of any file", {"file_path": "<file_path>"}),
            (self.list_files,
             "list_files",
             "List all files in the files directory and its subdirectories.",
             {"file_path": "<the path of the directory to list files from>"}),
            (self.get_file_info,
             "get_file_info",
             "Retrieve metadata about a specific file, including size, last modified, and created time.",
             {"file_path": "<the path of the file to get info about>"}),
            (self.search_files,
             "search_files",
             "Search for files and directories containing any of the specified search terms.",
             {
                 "search_terms": "<comma separated list of strings to search for in file/directory names>",
                 "path": "<optional: starting directory path for the search>",
                 "case_sensitive": "<optional: whether the search should be case sensitive (true/false)>"
             }),
            (self.content_search,
             "content_search",
             "Search for text within all files in a directory (like grep).",
             {
                 "search_term": "<text to search for within files>",
                 "path": "<optional: starting directory path for the search>",
                 "case_sensitive": "<optional: whether the search should be case sensitive (true/false)>"
             }),
             (self.content_search,
             "grep",
             "Search for text within all files in a directory (like grep).",
             {
                 "search_term": "<text to search for within files>",
                 "path": "<optional: starting directory path for the search>",
                 "case_sensitive": "<optional: whether the search should be case sensitive (true/false)>"
             }),
        ]

    def context_template(self, query: str, context: str, file_path: str) -> str:
        return f"""
Here is the contents of the file {file_path}:

{context}

Source: {file_path} 

"""
    def get_absolute_path(self, arguments):
        file_path = arguments.get("file_path", "") 
        abs_path = self.file_manager.get_absolute_path(file_path)
        yield ("result", f"The absolute path of {file_path} is {abs_path}")

    def get_file(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        if not file_path:
            yield ("end", "File path is required")
            return
        
        if file_path.endswith(".note"):
            yield ("result", "This is a note, please use the notes action to read it.")
            return

        file_manager = self.file_manager
        
        yield ("system", "Reading file: " + file_path)
        
        try:
            content = file_manager.get_file(file_path)
            if content is None:
                yield ("result", self.context_template(self.query, f"File {file_path} not found", file_path))
            else:
                yield ("result", f"here are the contents of the file {file_path} (the user has not seen these contents yet): " + self.context_template(self.query, content.decode('utf-8'), file_path))
        except Exception as e:
            yield ("result", self.context_template(self.query, f"Error reading file: {str(e)}", file_path))

    def list_files(self, arguments: Dict[str, Any]):
        file_manager = self.file_manager
        file_path = arguments.get("file_path", "")
        yield ("system", "Listing files under " + file_path)
        files = file_manager.list_files_recusive(file_path)
        yield ("result", 
               "I listed the files in " + file_path + " and here are the results: " + str("\n".join(files)))

    def get_file_info(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        if not file_path:
            yield ("end", "File path is required")
            return
        file_manager = self.file_manager
        yield ("system", "Getting file info: " + file_path)
        try:
            info = file_manager.get_file_info(file_path)
            if info is None:
                yield ("result", f"File {file_path} not found")
            else:
                info = json.dumps(info, indent=4)
                yield ("result", f"File info for {file_path}: {info}")
        except Exception as e:
            yield ("result", f"Error getting file info: {str(e)}")

    def search_files(self, arguments: Dict[str, Any]):
        """
        Search for files and directories containing specified search terms.
        """
        search_terms_str = arguments.get("search_terms", "")
        path = arguments.get("path", "")
        case_sensitive = arguments.get("case_sensitive", False)
        if isinstance(case_sensitive, str):
            case_sensitive = case_sensitive.lower() == "true"

        if not search_terms_str:
            yield ("end", "At least one search term is required")
            return

        # Split comma-separated terms and strip whitespace
        search_terms = [term.strip() for term in search_terms_str.split(",") if term.strip()]

        if not search_terms:
            yield ("end", "At least one valid search term is required")
            return

        yield ("system", f"Searching for files containing any of these terms: {', '.join(search_terms)} in {path} with case sensitivity: {case_sensitive}")
        
        try:
            matches = self.file_manager.search_files(search_terms, path, case_sensitive)
            if matches:
                yield ("result", f"Found {len(matches)} matching files/directories:\n" + "\n".join(matches))
            else:
                yield ("result", "No files or directories found matching the search terms.")
        except Exception as e:
            yield ("result", f"Error searching files: {str(e)}")

    def content_search(self, arguments: Dict[str, Any]):
        """
        Search for text content within files.
        """
        search_term = arguments.get("search_term", "")
        path = arguments.get("path", "")
        case_sensitive = arguments.get("case_sensitive", "false").lower() == "true"

        if not search_term:
            yield ("end", "Search term is required")
            return

        yield ("system", f"Searching for files containing the text: {search_term} in {path} with case sensitivity: {case_sensitive}")
        
        try:
            matches = self.file_manager.content_search(search_term, path, case_sensitive)
            if matches:
                yield ("result", f"Found matches in files:\n" + "\n".join(matches))
            else:
                yield ("result", "No files found containing the search term.")
        except Exception as e:
            yield ("result", f"Error searching file contents: {str(e)}")

    def additional_notes(self):
        return "You can read any file on the file system.  You can get a list of files in any directory on the file system.  Files are generally written in " + self.config_manager.get_sandbox_directory_path() + "."
        