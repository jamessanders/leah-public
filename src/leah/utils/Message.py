import uuid
import time
from enum import Enum
from typing import Dict, Any
from datetime import datetime


class MessageType(Enum):
    DIRECT = "direct"
    CHANNEL = "channel"
    SYSTEM = "system"
    HANGUP = "hangup"


class Message:
    
    def __init__(self, from_user: str, via_channel: str, content: str, type: MessageType = None, thread=None):
        self.sent_at = time.time()
        self.id = str(uuid.uuid4())
        self.from_user = from_user
        self.via_channel = via_channel
        self.content = content
        self.type = type
        self.thread = thread
        if type is None:
            self.set_type(MessageType.CHANNEL if via_channel.startswith("@") else MessageType.DIRECT)
        if not isinstance(self.type, MessageType):
            raise ValueError("type must be a MessageType")
       

    def __str__(self):
        return f"Message(from_user={self.from_user}, via_channel={self.via_channel}, content={self.content}, type={self.type.value})"
    
    def set_type(self, type: MessageType):
        self.type = type

    def set_to_direct(self):
        self.set_type(MessageType.DIRECT)
    
    def set_to_channel(self):
        self.set_type(MessageType.CHANNEL)

    def set_to_system(self):
        self.set_type(MessageType.SYSTEM)

    def is_channel(self) -> bool:
        return self.type == MessageType.CHANNEL

    def is_direct(self) -> bool:
        return self.type == MessageType.DIRECT

    def is_system(self) -> bool:
        return self.type == MessageType.SYSTEM

    def relative_sent_at(self) -> str:
        """Returns a human readable relative time difference.
        Examples: 'Just now', '2 minutes ago', '1 hour ago', '2 days ago'"""
        now = time.time()
        diff = now - self.sent_at
        
        if diff < 60:  # Less than a minute
            seconds = int(diff)
            return f"{seconds} second{'s' if seconds != 1 else ''} ago"
        elif diff < 3600:  # Less than an hour
            minutes = int(diff / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < 86400:  # Less than a day
            hours = int(diff / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < 604800:  # Less than a week
            days = int(diff / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif diff < 2592000:  # Less than a month
            weeks = int(diff / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif diff < 31536000:  # Less than a year
            months = int(diff / 2592000)
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = int(diff / 31536000)
            return f"{years} year{'s' if years != 1 else ''} ago"

    def get_readable_sent_at(self) -> str:
        """Returns the sent_at timestamp in a human readable format.
        Format: 'January 1, 2024 at 12:34 PM'"""
        return datetime.fromtimestamp(self.sent_at).strftime('%B %d, %Y at %I:%M %p')

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for storage"""
        return {
            "id": self.id,
            "sent_at": self.sent_at,
            "from_user": self.from_user,
            "via_channel": self.via_channel,
            "content": self.content,
            "type": self.type.value,
            "thread": self.thread
        } 