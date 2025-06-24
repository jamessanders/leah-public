import uuid
import threading
import json
import os
from typing import Callable, Dict, List, Optional, Any, Generator
from collections import defaultdict
from queue import Queue
import time
import shutil

from leah.config.LocalConfigManager import LocalConfigManager
from leah.utils.Message import Message, MessageType


class JunctionActor:
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance of JunctionActor exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize instance variables
            cls._instance._pubsub = PubSub.get_instance()
            cls._instance._subscribed_channels = set()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'JunctionActor':
        """
        Get the singleton instance of JunctionActor.
        
        Returns:
            JunctionActor: The singleton instance
        """
        if cls._instance is None:
            cls._instance = JunctionActor()
        return cls._instance
    
    def __init__(self):
        # No initialization needed here since it's done in __new__
        self.connections = {}
        pass

    def join(self, channel_in, channel_out):
        key = channel_in+channel_out    
        if key in self._subscribed_channels:
            return
        self._subscribed_channels.add(key)

        callback = self._handle_message(channel_in, channel_out)
        if channel_in not in self.connections:
            self.connections[channel_in] = {}
        if channel_out not in self.connections[channel_in]:
            self.connections[channel_in][channel_out] = []

        self.connections[channel_in][channel_out].append(callback)
        self._pubsub.subscribe(channel_in, callback)

    def leave(self, channel_in, channel_out):
        key = channel_in+channel_out
        if key in self._subscribed_channels:
            self._subscribed_channels.remove(key)
            self._pubsub.unsubscribe(channel_in, self.connections[channel_in][channel_out])

    def _handle_message(self, channel_in, channel_out):
        def pub(message):
            self._pubsub.publish(channel_out, message)
        return pub


class PubSub:
    """A simple publish-subscribe implementation for message distribution."""
    
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance of PubSub exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize the instance
            cls._instance._subscribers = defaultdict(list)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'PubSub':
        """
        Get the singleton instance of PubSub.
        
        Returns:
            PubSub: The singleton instance
        """
        if cls._instance is None:
            cls._instance = PubSub()
        return cls._instance
    
    def __init__(self):
        self.compact_enabled = False
        self.MAX_THREADS = 4
        self.config_manager = LocalConfigManager("system", "chat")
        self.junction_actor = JunctionActor.get_instance()
        self.overwatch_channel = "$$overwatch$$"

    def _get_channel_storage_path(self, channel_id: str) -> str:
        """Get the storage path for a channel's messages"""
        safe_channel = channel_id.replace('/', '_').replace('\\', '_').replace('#',"group_").replace("@","user_").replace("->","to")
        return self.config_manager.get_path(f"channels/{safe_channel}/messages.json")

    def _store_message(self, channel_id: str, message: Message) -> None:
        """Store a message in the channel's message history"""
        if message.type == MessageType.HANGUP:
            return
        if "#system-chan" in message.via_channel:
            return
        
        storage_path = self._get_channel_storage_path(channel_id)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Load existing messages
        messages = []
        if os.path.exists(storage_path):
            try:
                with open(storage_path, 'r') as f:
                    messages = json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Add new message
        messages.append(message.to_dict())
        
        # Save messages back to file
        with open(storage_path, 'w') as f:
            json.dump(messages, f, indent=2)

    def bind_channels(self, channel_in, channel_out):
        self.junction_actor.join(channel_in, channel_out)

    def unbind_channels(self, channel_in, channel_out):
        self.junction_actor.leave(channel_in, channel_out)

    def get_channel_messages(self, channel_id: str) -> List[Message]:
        """
        Get all messages for a channel.
        
        Args:
            channel_id (str): The channel to get messages for
            
        Returns:
            List[Message]: List of messages in the channel
        """
        storage_path = self._get_channel_storage_path(channel_id)
        
        if not os.path.exists(storage_path):
            return []
            
        try:
            with open(storage_path, 'r') as f:
                message_dicts = json.load(f)
                
            messages = []
            for msg_dict in message_dicts:
                message = Message(
                    from_user=msg_dict["from_user"],
                    via_channel=msg_dict["via_channel"],
                    content=msg_dict["content"],
                    type=MessageType(msg_dict["type"]),
                    thread=msg_dict.get("thread", None)
                )
                message.id = msg_dict["id"]
                message.sent_at = msg_dict["sent_at"]
                messages.append(message)
            return messages
        except (json.JSONDecodeError, KeyError) as e: 
            print(e)
            return []

    def clear_channel_messages(self, channel_id: str) -> None:
        """
        Clear all messages for a channel.
        
        Args:
            channel_id (str): The channel to clear messages for
        """
        storage_path = self._get_channel_storage_path(channel_id)
        
        # If the file doesn't exist, no need to backup or clear
        if not os.path.exists(storage_path):
            return
            
        # Create backup directory
        backup_dir = os.path.join(os.path.dirname(storage_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_filename = f"messages_{timestamp}.json"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy current messages to backup
        shutil.copy2(storage_path, backup_path)
        
        # Now clear the messages
        with open(storage_path, 'w') as f:
            json.dump([], f)

    def subscribe(self, channel_id: str, callback: Callable) -> None:
        """
        Subscribe to a specific channel with a callback function.
        
        Args:
            channel_id (str): The channel identifier to subscribe to
            callback (Callable): The callback function to be called when a message is published
        """
        self._subscribers[channel_id].append(callback)
    
    def overwatch(self, callback: Callable) -> None:
        """
        Subscribe to all channels with a callback function.
        """
        self.subscribe(self.overwatch_channel, callback)

    
    def publish(self, channel_id: str, message: Message) -> None:
        """
        Publish a message to a specific channel.
        
        Args:
            channel_id (str): The channel identifier to publish to  
            message (Message): The message to be published
        """
        if not isinstance(message, Message):
            raise ValueError("Message must be an instance of Message")
        # Store the message before publishing
        self._store_message(channel_id, message)
        self._run_overwatch(channel_id, message)
        self._run_publish(channel_id, message)


    def _run_overwatch(self, channel_id: str, message: Message) -> None:
        """
        Run the overwatch callback.
        """
        for callback in self._subscribers[self.overwatch_channel]:
            callback(channel_id, message)

    def _run_publish(self, channel_id: str, message: Message) -> None:
        """
        Publish a message to a specific channel.
        
        Args:
            channel_id (str): The channel identifier to publish to
            message (Message): The message to be published
        """
        for callback in self._subscribers[channel_id]:
            try:
                callback(message)
            except Exception as e:
                # Log the full traceback for better debugging
                import traceback
                print(f"Error in subscriber callback for channel {channel_id}:")
                print(traceback.format_exc())

    def unsubscribe(self, channel_id: str, callback: Callable = None) -> None:
        """
        Unsubscribe a callback from a specific channel.
        
        Args:
            channel_id (str): The channel identifier to unsubscribe from
            callback (Callable): The callback function to be removed
        """
        if channel_id in self._subscribers:
            try:
                if not callback:
                    self._subscribers[channel_id] = []
                else:   
                    self._subscribers[channel_id].remove(callback)
            except ValueError:
                pass  # Callback wasn't in the list
            
            # Clean up empty channel lists and release the lock
            if not self._subscribers[channel_id]:
                del self._subscribers[channel_id]

    def watch(self, channel_id: str, timeout: Optional[float] = None) -> Generator[Any, None, None]:
        """
        Watch a channel and yield messages as they arrive.
        
        Args:
            channel_id (str): The channel identifier to watch
            timeout (Optional[float]): Maximum time to wait between messages in seconds.
                                     If None, will wait indefinitely.
        
        Yields:
            Any: Messages as they are received from the channel
        
        Raises:
            TimeoutError: If timeout is specified and no messages are received within the timeout period
        """
        message_queue = Queue()
        
        def queue_callback(message: Message) -> None:
            message_queue.put(message)
        
        # Subscribe to the channel with our queue callback
        self.subscribe(channel_id, queue_callback)
        start_time = time.time()
        message = None
        while True:
            if timeout is not None and time.time() - start_time > timeout:
                break
            else:
                # Wait indefinitely for messages
                if not message_queue.empty():
                    message = message_queue.get()
                    yield message
                    if message.type == MessageType.HANGUP:
                        break
                else:
                    time.sleep(0.1)   
        # Always unsubscribe the queue callback
        ## delete the message queue
        del message_queue
        self.unsubscribe(channel_id, queue_callback) 