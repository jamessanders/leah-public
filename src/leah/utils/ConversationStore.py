import os
import pickle
import json
from typing import List, Dict, Any, Optional, Set
from leah.utils.FileManager import FileManager

class ConversationStore:
    def __init__(self, file_manager: FileManager):
        """
        Initialize the ConversationStore with a FileManager instance.
        
        Args:
            file_manager (FileManager): The FileManager instance to use for storing conversations
        """
        self.file_manager = file_manager
        
    def save_conversation(self, conversation_id: str, history: List[Dict[str, Any]]) -> None:
        """
        Save a conversation history to a pickle file.
        
        Args:
            conversation_id (str): Unique identifier for the conversation
            history (List[Dict[str, Any]]): The conversation history to save
        """
        # Ensure the conversation ID is safe for filenames
        safe_id = conversation_id.replace('/', '_').replace('\\', '_')
        filename = f"conversations/{safe_id}/data.pickle"
        
        # Pickle the conversation history
        pickled_data = pickle.dumps(history)
        
        # Save using file manager
        self.file_manager.put_file(filename, pickled_data)
        
    def load_conversation(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load a conversation history from a pickle file.
        
        Args:
            conversation_id (str): Unique identifier for the conversation
            
        Returns:
            Optional[List[Dict[str, Any]]]: The conversation history if found, None otherwise
        """
        # Ensure the conversation ID is safe for filenames
        safe_id = conversation_id.replace('/', '_').replace('\\', '_')
        filename = f"conversations/{safe_id}/data.pickle"
        
        # Try to load using file manager
        data = self.file_manager.get_file(filename)
        if data is not None:
            try:
                return pickle.loads(data)
            except pickle.UnpicklingError:
                return None
        return None
        
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation history file.
        
        Args:
            conversation_id (str): Unique identifier for the conversation
            
        Returns:
            bool: True if file was deleted, False if file didn't exist
        """
        # Ensure the conversation ID is safe for filenames
        safe_id = conversation_id.replace('/', '_').replace('\\', '_')
        filename = f"conversations/{safe_id}/data.pickle"
        
        return self.file_manager.delete_file(filename)

    def add_watched_inbox(self, conversation_id: str, inbox_path: str) -> None:
        """
        Add an inbox path to the list of watched inboxes for a conversation.
        
        Args:
            conversation_id (str): Unique identifier for the conversation
            inbox_path (str): Path to the inbox to watch
        """
        safe_id = conversation_id.replace('/', '_').replace('\\', '_')
        filename = f"conversations/{safe_id}/watching.json"
        
        # Load existing watched inboxes
        watched_inboxes = set()
        data = self.file_manager.get_file(filename)
        if data is not None:
            try:
                watched_inboxes = set(json.loads(data.decode()))
            except json.JSONDecodeError:
                pass
        
        # Add new inbox and save
        watched_inboxes.add(inbox_path)
        self.file_manager.put_file(filename, json.dumps(list(watched_inboxes)).encode())
        
    def remove_watched_inbox(self, conversation_id: str, inbox_path: str) -> bool:
        """
        Remove an inbox path from the list of watched inboxes for a conversation.
        
        Args:
            conversation_id (str): Unique identifier for the conversation
            inbox_path (str): Path to the inbox to stop watching
            
        Returns:
            bool: True if the inbox was removed, False if it wasn't being watched
        """
        safe_id = conversation_id.replace('/', '_').replace('\\', '_')
        filename = f"conversations/{safe_id}/watching.json"
        
        # Load existing watched inboxes
        watched_inboxes = set()
        data = self.file_manager.get_file(filename)
        if data is not None:
            try:
                watched_inboxes = set(json.loads(data.decode()))
            except json.JSONDecodeError:
                return False
        
        # Remove inbox if present
        if inbox_path not in watched_inboxes:
            return False
            
        watched_inboxes.remove(inbox_path)
        self.file_manager.put_file(filename, json.dumps(list(watched_inboxes)).encode())
        return True
        
    def get_watched_inboxes(self, conversation_id: str) -> Set[str]:
        """
        Get the set of watched inboxes for a conversation.
        
        Args:
            conversation_id (str): Unique identifier for the conversation
            
        Returns:
            Set[str]: Set of inbox paths being watched
        """
        if not conversation_id:
            return set()
        safe_id = conversation_id.replace('/', '_').replace('\\', '_')
        filename = f"conversations/{safe_id}/watching.json"
        # Load existing watched inboxes
        data = self.file_manager.get_file(filename)
        if data is not None:
            try:
                return set(json.loads(data.decode()))
            except json.JSONDecodeError:
                return set()
        return set() 