import os
import pickle
from typing import List, Dict, Any, Optional
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