from datetime import datetime
from typing import Any, Dict, List
from leah.actions.IActions import IAction
from leah.utils.GlobalFileManager import GlobalFileManager
from leah.utils.Message import Message,MessageType
from leah.utils.PubSub import PubSub
import os
import requests

class FileWriteAction(IAction): 
    def __init__(self, config_manager, persona, query, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.file_manager = GlobalFileManager(config_manager, '/', config_manager.get_sandbox_directory_path())

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
             {"file_path": "<the path of the file to delete>"}),
            (self.download_file,
             "download_file",
             "Download a file from a URL and save it to the specified file path. The file path can include subdirectories which will be created as needed. This is best for downloading images and other binary files.",
             {"url": "<the url to download>", "file_path": "<the path to save the file>"})
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
            full_path = os.path.abspath(file_manager.put_file(file_path, content.encode('utf-8')))
            pubsub = PubSub.get_instance()
            if self.chat_app.channel_id:
                pubsub.publish(self.chat_app.channel_id, Message("@" + self.persona, self.chat_app.channel_id, f"Created file: {file_path}"))
            yield ("result", f"I have saved a file to {full_path}")
        except Exception as e:
            yield ("result", f"I attempted to save a file to {file_path} but received the following error: {str(e)}")

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
            yield ("result", f"I have moved a file from {source_path} to {actual_path}")
        except FileNotFoundError:
            yield ("result", f"I attempted to move a file from {source_path} to {target_path} but the source file was not found")
        except Exception as e:
            yield ("result", f"I attempted to move a file from {source_path} to {target_path} but received the following error: {str(e)}")

    def delete_file(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        if not file_path:
            yield ("end", "File path is required")
            return
        
        yield ("system", f"Deleting file {file_path}")
        file_manager = self.file_manager
        
        try:
            if file_manager.delete_file(file_path):
                yield ("result", f"I have deleted a file from {file_path} (moved to backup)")
            else:
                yield ("result", f"I attempted to delete a file from {file_path} but it was not found")
        except Exception as e:
            yield ("result", f"I attempted to delete a file from {file_path} but received the following error: {str(e)}")

    def download_file(self, arguments: Dict[str, Any]):
        url = arguments.get("url", "")
        file_path = arguments.get("file_path", "")
        if not url or not file_path:
            yield ("end", "URL and file path are required")
            return
        yield ("system", f"Downloading file from {url} to {file_path}")
        try:
            response = requests.get(url, stream=True)
            try:
                response.raise_for_status()
            except Exception as e:
                yield ("result", f"I attempted to download the file from {url} but received the following error: {str(e)}")
                return
            content = response.content
            full_path = os.path.abspath(self.file_manager.put_file(file_path, content))
            pubsub = PubSub.get_instance()
            if self.chat_app.channel_id:
                pubsub.publish(self.chat_app.channel_id, Message("@" + self.persona, self.chat_app.channel_id, f"Downloaded file: {file_path} from {url}"))
            yield ("result", f"I have downloaded the file from {url} and saved it to {full_path}")
        except Exception as e:
            yield ("result", f"I attempted to download the file from {url} but received the following error: {str(e)}")

    def additional_notes(self):
        return "You can only write to files under the directory " + self.config_manager.get_sandbox_directory_path() + ". "
    
    