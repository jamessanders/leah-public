from datetime import datetime
from typing import Any, Dict, List
from leah.llm.ChatApp import ChatApp
from leah.actions.IActions import IAction
from leah.utils.FileManager import FileManager
from leah.utils.FilesSandbox import FilesSandbox

class FileWriteAction(IAction): 
    def __init__(self, config_manager, persona, query, chat_app: ChatApp):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.file_manager = FilesSandbox(config_manager.get_file_manager(), "sandbox")

    def getTools(self):
        return [
            (self.put_file, 
             "put_file", 
             "Save contents to a file. Always use relative paths. The file path can include subdirectories which will be created as needed.", 
             {"file_path": "<file_path>", "content": "<file_contents>"}),
            (self.put_file, 
             "update_file", 
             "Update contents of a file. The file path can include subdirectories which will be created as needed.", 
             {"file_path": "<the path of the file to update>", "content": "<the content to update the file with>"}),
            (self.move_file,
             "move_file",
             "Move a file from one location to another. Creates necessary directories in the target path.",
             {"source_path": "<the path of the file to move>", "target_path": "<the path to move the file to>"}),
            (self.delete_file,
             "delete_file",
             "Delete a file. The file is moved to a backup directory rather than being permanently deleted.",
             {"file_path": "<the path of the file to delete>"})
        ]

    def context_template(self, query: str, context: str, file_path: str) -> str:
        return f"""
Here is the contents of the file {file_path}:

{context}

Source: {file_path} 

"""

    def put_file(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        content = arguments.get("content", "")
        if not file_path or not content:
            yield ("end", "File path and content are required")
            return
        
        file_manager = self.file_manager
        
        yield ("system", "Saving file: " + file_path)

        try:
            file_manager.put_file(file_path, content.encode('utf-8'))
            yield ("end", f"File {file_path} has been saved")
        except Exception as e:
            yield ("end", f"Error saving file {file_path}: {str(e)}")

    def move_file(self, arguments: Dict[str, Any]):
        source_path = arguments.get("source_path", "")
        target_path = arguments.get("target_path", "")
        if not source_path or not target_path:
            yield ("end", "Source path and target path are required")
            return
        
        yield ("system", f"Moving file from {source_path} to {target_path}")
        file_manager = self.file_manager
        
        try:
            actual_path = file_manager.move_file(source_path, target_path)
            yield ("end", f"File moved successfully to {actual_path}")
        except FileNotFoundError:
            yield ("end", f"Source file {source_path} not found")
        except Exception as e:
            yield ("end", f"Error moving file: {str(e)}")

    def delete_file(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        if not file_path:
            yield ("end", "File path is required")
            return
        
        yield ("system", f"Deleting file {file_path}")
        file_manager = self.file_manager
        
        try:
            if file_manager.delete_file(file_path):
                yield ("end", f"File {file_path} has been deleted (moved to backup)")
            else:
                yield ("end", f"File {file_path} not found")
        except Exception as e:
            yield ("end", f"Error deleting file: {str(e)}")

    def additional_notes(self):
        file_manager = self.file_manager
        all_files = file_manager.get_all_files()
        if all_files:
            return "Here are some current files you have that you can modify: " + str(", ".join(all_files))
        return "" 