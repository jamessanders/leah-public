from queue import Queue
from threading import Lock, Thread
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional, Set, Callable, Any, TYPE_CHECKING
from datetime import datetime
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

if TYPE_CHECKING:
    from leah.config.LocalConfigManager import LocalConfigManager

@dataclass
class Message:
    body: Any
    return_inbox_id: str
class MessageHandler(ABC):
    @abstractmethod
    def handle_message(self, message: Message) -> None:
        """Handle a single message."""
        pass

class MailMan:
    MAX_WORKERS = 8

    def __init__(self, 
                 post_office: 'PostOffice', 
                 watched_inboxes: List[str],
                 message_handler: MessageHandler,
                 check_interval: float = 1.0):
        """
        Initialize the MailMan.
        
        Args:
            post_office: PostOffice instance to watch
            watched_inboxes: List of inboxes to monitor
            message_handler: MessageHandler instance to process messages
            check_interval: How often to check for new messages (in seconds)
        """
        self._post_office = post_office
        self._watched_inboxes = set(watched_inboxes)
        self._message_handler = message_handler
        self._check_interval = check_interval
        self._active = False
        self._watch_thread: Optional[Thread] = None
        self._lock = Lock()
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS,
            thread_name_prefix="MailMan_Handler"
        )
        self._pending_messages: Queue[Message] = Queue()
        
    def start(self) -> None:
        """Start watching for messages."""
        with self._lock:
            if not self._active:
                self._active = True
                self._watch_thread = Thread(target=self._watch_loop, daemon=True, name="MailMan_Watcher")
                self._watch_thread.start()
                
    def stop(self) -> None:
        """Stop watching for messages and clean up resources."""
        with self._lock:
            if self._active:
                self._active = False
                # Don't join the thread since it's a daemon
                self._watch_thread = None
                # Shutdown thread pool without waiting
                self._thread_pool.shutdown(wait=False)
                
    def _watch_loop(self) -> None:
        """Main loop for watching messages."""
        while self._active:
            self._check_messages()
            self._process_pending_messages()
            time.sleep(self._check_interval)
            
    def _check_messages(self) -> None:
        """Check for new messages in watched inboxes."""
        active_inboxes = self._post_office.list_active_inboxes()
        # If watched_emails is empty, watch all inboxes
        watched_active = active_inboxes if not self._watched_inboxes else active_inboxes.intersection(self._watched_inboxes)
        
        for inbox in watched_active:
            message = self._post_office.check_messages(inbox)
            if message:
                self._pending_messages.put(message)
                
    def _process_pending_messages(self) -> None:
        """Process pending messages using the thread pool."""
        while not self._pending_messages.empty():
            try:
                message = self._pending_messages.get_nowait()
                self._thread_pool.submit(self._message_handler.handle_message, message)
            except Queue.Empty:
                break
            
    def is_active(self) -> bool:
        """Check if the MailMan is currently active."""
        return self._active
        
    def get_active_handler_count(self) -> int:
        """Get the number of active message handler threads."""
        return len([t for t in self._thread_pool._threads if t.is_alive()])

    def get_pending_message_count(self) -> int:
        """Get the number of messages waiting to be processed."""
        return self._pending_messages.qsize()

# Example message handler
class PrintMessageHandler(MessageHandler):
    def handle_message(self, message: Message) -> None:
        """Simply print the message details."""
        print(f"New message in inbox {message.return_inbox_id}")
        print(f"Body: {message.body}")
        print("-" * 50)

class PostOffice:
    _instance = None
    _instance_lock = Lock()

    def __new__(cls):
        """Ensure only one instance of PostOffice is created (singleton pattern)."""
        return super().__new__(cls)

    @classmethod
    def get_instance(cls) -> 'PostOffice':
        """Get the singleton instance of PostOffice."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    instance = cls()
                    instance._initialized = False
                    instance.__init__()
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        """Initialize the PostOffice instance (only runs once due to singleton pattern)."""
        if not hasattr(self, '_initialized') or not self._initialized:
            self._inboxes: Dict[str, Queue[Message]] = {}
            self._inbox_locks: Dict[str, Lock] = {}
            self._closed_inboxes: Set[str] = set()
            self._lock = Lock()
            self._initialized = True
    
    def create_inbox(self, id: str) -> bool:
        """Create a new inbox for the given email if it doesn't exist."""
        with self._lock:
            if id not in self._inboxes:
                self._inboxes[id] = Queue()
                self._inbox_locks[id] = Lock()
                return True
            return False
    
    def delete_inbox(self, id: str) -> bool:
        """Delete an inbox for the given email if it exists."""
        with self._lock:
            if id in self._inboxes:
                del self._inboxes[id]
                del self._inbox_locks[id]
                self._closed_inboxes.discard(id)
                return True
            return False
        
    def has_inbox(self, id: str) -> bool:
        """Check if the specified inbox exists."""
        return id in self._inboxes
    
    def send_message(self, 
                     to_inbox_id: str,
                     return_inbox_id: str,
                     body: Any) -> bool:
        """
        Send a message to the specified inbox.
        If the inbox is closed, it will be automatically reopened to accept this message.
        """
        if to_inbox_id not in self._inboxes:
            return False
            
        message = Message(
            body=body,
            return_inbox_id=return_inbox_id
        )
        
        with self._lock:
            # Automatically reopen the inbox when sending a message
            self._closed_inboxes.discard(to_inbox_id)
            
            with self._inbox_locks[to_inbox_id]:
                self._inboxes[to_inbox_id].put(message)
        return True
    
    def check_messages(self, id: str) -> Optional[Message]:
        """Check for messages in the specified inbox."""
        if id not in self._inboxes:
            return None
            
        with self._inbox_locks[id]:
            if not self._inboxes[id].empty():
                return self._inboxes[id].get()
        return None
    
    def has_messages(self, id: str) -> bool:
        """Check if the specified inbox has any messages."""
        if id not in self._inboxes:
            return False
            
        with self._inbox_locks[id]:
            return not self._inboxes[id].empty()
    
    def get_inbox_size(self, id: str) -> int:
        """Get the number of messages in the specified inbox."""
        if id not in self._inboxes:
            return 0
            
        with self._inbox_locks[id]:
            return self._inboxes[id].qsize()
            
    def list_active_inboxes(self) -> Set[str]:
        """Return a set of email addresses for inboxes that currently have messages."""
        active_inboxes = set()
        with self._lock:
            for id in self._inboxes:
                if self.has_messages(id):
                    active_inboxes.add(id)
        return active_inboxes

    def is_inbox_closed(self, id: str) -> bool:
        """Check if the specified inbox is closed for new messages."""
        return id in self._closed_inboxes

    def stream_messages_till_closed_or_timeout(self, inbox_id: str, timeout: float) -> Generator:
        """Stream messages from the inbox until it is closed or the timeout is reached."""
        start_time = time.time()
        while self.has_inbox(inbox_id):
            if self.has_messages(inbox_id):
                yield self.check_messages(inbox_id)
            if self.is_inbox_closed(inbox_id) and not self.has_messages(inbox_id):
                break
            if time.time() - start_time > timeout:
                break
            time.sleep(0.1)


    def close_inbox(self, id: str) -> bool:
        """
        Close an inbox for new messages. Closed inboxes can still be read but won't accept new messages.
        Returns True if the inbox was closed, False if it doesn't exist.
        """
        if id not in self._inboxes:
            return False
            
        with self._lock:
            self._closed_inboxes.add(id)
        return True

    def open_inbox(self, id: str) -> bool:
        """
        Open a closed inbox to allow new messages.
        Returns True if the inbox was opened, False if it doesn't exist.
        """
        if id not in self._inboxes:
            return False
            
        with self._lock:
            self._closed_inboxes.discard(id)
        return True
