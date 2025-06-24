import json
import os
from typing import Dict, List, Set
from pathlib import Path
from leah.config.LocalConfigManager import LocalConfigManager
from leah.utils.PubSub import PubSub
import threading

class SubscriptionService:
    _instance = None
    
    def __new__(cls):
        """Ensure only one instance of SubscriptionService exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Initialize instance variables
            cls._instance.subscriptions: Dict[str, Set[str]] = {}
            cls._instance.admin_subscriptions: Dict[str, Set[str]] = {}
            cls._instance._write_lock = threading.Lock()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'SubscriptionService':
        """
        Get the singleton instance of SubscriptionService.
        
        Returns:
            SubscriptionService: The singleton instance
        """
        if cls._instance is None:
            cls._instance = SubscriptionService()
        return cls._instance
    
    def __init__(self):
        """Initialize the subscription service."""
        self.config_manager = LocalConfigManager("system", "subscriptions")
        self.subscriptions: Dict[str, Set[str]] = {}
        self.admin_subscriptions: Dict[str, Set[str]] = {}
        self._pubsub = PubSub.get_instance()
        self._write_lock = threading.Lock()
        self._load_subscriptions()
        self.bind_subscribers()
    
    def _get_storage_path(self) -> str:
        """Get the storage path for subscriptions"""
        return self.config_manager.get_path("subscriptions.json")

    def _load_subscriptions(self, force_reload: bool = True) -> None:
        """Load subscriptions from disk if the file exists."""
        storage_path = self._get_storage_path()
        if os.path.exists(storage_path):
            try:
                with open(storage_path, 'r') as f:
                    # Convert lists back to sets when loading
                    data = json.load(f)
                    self.subscriptions = {
                        user: set(channels) 
                        for user, channels in data.get('subscriptions', {}).items()
                    }
                    self.admin_subscriptions = {
                        channel: set(admins)
                        for channel, admins in data.get('admins', {}).items()
                    }
            except json.JSONDecodeError:
                print(f"Error loading subscriptions from {storage_path}")
                if force_reload:
                    self._load_subscriptions(False)

    def _save_subscriptions(self) -> None:
        """Save subscriptions to disk."""
        storage_path = self._get_storage_path()
        
        # Create directory if it doesn't exist
        Path(storage_path).parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            try:
                # Convert sets to lists for JSON serialization
                data = {
                    'subscriptions': {
                        user: list(channels) 
                        for user, channels in self.subscriptions.items()
                    },
                    'admins': {
                        channel: list(admins)
                        for channel, admins in self.admin_subscriptions.items()
                    }
                }
                with open(storage_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error saving subscriptions to {storage_path}: {e}")

    def bind_subscribers(self) -> None:
        """
        Bind all users to their subscribed channels using PubSub.
        This ensures messages from subscribed channels are delivered to users.
        """
        for user_id, channels in self.subscriptions.items():
            for channel in channels:
                self._pubsub.bind_channels(channel, user_id)
                
    def subscribe(self, user_id: str, channel: str) -> None:
        """Subscribe a user to a channel.
        
        Args:
            user_id (str): The ID of the user
            channel (str): The channel to subscribe to
        """
        
        if (channel.startswith("@")):
            raise Exception("Cannot subscribe to a direct message channel")
        
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        self.subscriptions[user_id].add(channel)
        self._save_subscriptions()
        
        # Bind the new subscription immediately
        self.connect(user_id, channel)

    def connect(self, user_id: str, channel: str) -> None:
        self._pubsub.bind_channels(channel, user_id)

    def disconnect(self, user_id: str, channel: str) -> None:
        self._pubsub.unbind_channels(channel, user_id)

    def unsubscribe(self, user_id: str, channel: str) -> None:
        """Unsubscribe a user from a channel.
        
        Args:
            user_id (str): The ID of the user
            channel (str): The channel to unsubscribe from
        """
        if user_id in self.subscriptions:
            self.subscriptions[user_id].discard(channel)
            self._save_subscriptions()
            self.disconnect(user_id, channel)

    def is_subscribed(self, user_id: str, channel: str) -> bool:
        """Check if a user is subscribed to a channel.
        
        Args:
            user_id (str): The ID of the user
            channel (str): The channel to check subscription for    
        """
        return user_id in self.get_channel_subscribers(channel)

    def get_user_subscriptions(self, user_id: str) -> Set[str]:
        """Get all channels a user is subscribed to.
        
        Args:
            user_id (str): The ID of the user
            
        Returns:
            Set[str]: Set of channel names the user is subscribed to
        """
        return self.subscriptions.get(user_id, set())

    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get all users subscribed to a channel.
        
        Args:
            channel (str): The channel name
            
        Returns:
            List[str]: List of user IDs subscribed to the channel
        """
        return [
            user_id 
            for user_id, channels in self.subscriptions.items() 
            if channel in channels
        ]

    def make_admin(self, user_handle: str, channel: str) -> None:
        """Make a user an admin of a channel.
        
        Args:
            user_handle (str): The handle of the user (e.g. @user)
            channel (str): The channel to make the user an admin of
        """
        # Ensure user is subscribed to the channel first
        if not self.is_subscribed(user_handle, channel):
            self.subscribe(user_handle, channel)
            
        if channel not in self.admin_subscriptions:
            self.admin_subscriptions[channel] = set()
            
        self.admin_subscriptions[channel].add(user_handle)
        self._save_subscriptions()

    def get_channel_admins(self, channel: str) -> List[str]:
        """Get all admin users for a channel.
        
        Args:
            channel (str): The channel name
            
        Returns:
            List[str]: List of user handles who are admins of the channel
        """
        return list(self.admin_subscriptions.get(channel, set()))

    def is_admin(self, user_handle: str, channel: str) -> bool:
        """Check if a user is an admin of a channel.
        
        Args:
            user_handle (str): The handle of the user (e.g. @user)
            channel (str): The channel to check admin status for
            
        Returns:
            bool: True if the user is an admin of the channel, False otherwise
        """
        return user_handle in self.admin_subscriptions.get(channel, set())
