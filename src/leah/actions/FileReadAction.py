from datetime import datetime
from typing import Any, Dict, List
from leah.llm.ChatApp import ChatApp
from leah.actions.IActions import IAction
from leah.utils.FileManager import FileManager
from leah.utils.FilesSandbox import FilesSandbox

class FileReadAction(IAction): 
    def __init__(self, config_manager, persona, query, chat_app: ChatApp):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.file_manager = FilesSandbox(config_manager.get_file_manager(), "sandbox")

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
             {}),
            (self.list_files_by_size,
             "list_files_by_size",
             "List files ordered by size from largest to smallest, optionally limited to a maximum number.",
             {"max_files": "<optional maximum number of files to list>"})
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
        yield ("system", "Listing files")
        file_manager = self.file_manager
        files = file_manager.get_all_files()
        yield ("result", "Here are all the files you have: " + str(", ".join(files)) + "\nAnswer the query based on this information, the query is: " + self.query)

    def list_files_by_size(self, arguments: Dict[str, Any]):
        yield ("system", "Listing files by size")
        file_manager = self.file_manager
        max_files = arguments.get("max_files", None)
        if max_files is not None:
            try:
                max_files = int(max_files)
            except ValueError:
                max_files = None
        files = file_manager.get_files_by_size(max_files)
        yield ("result", "Here are your files ordered by size: " + str(", ".join(files)) + "\nAnswer the query based on this information, the query is: " + self.query)

    def additional_notes(self):
        file_manager = self.file_manager
        all_files = file_manager.get_all_files()
        if all_files:
            return "Here are some current files you have that you can read: " + str(", ".join(all_files))
        return "" 