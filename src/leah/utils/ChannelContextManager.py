from enum import Enum
import pickle
import os
import threading
from typing import Any, Dict, Optional
import uuid

from leah.config.LocalConfigManager import LocalConfigManager

class ContextType(Enum):
    NOTE = "note"

    def __str__(self):
        return self.value
    
    def __repr__(self):
        return self.value


class ChannelContextManager:
    def __init__(self):
        self.config_manager = LocalConfigManager("system", "subscriptions")
        self.path = self.config_manager.get_path("contexts.pkl")
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "wb") as f:
                pickle.dump({}, f)
        self.contexts = {}
        self.lock = threading.Lock()
        self.load_contexts()

    def get_context(self, channel: str) -> Optional[Dict[str, Any]]:
        print(self.contexts)
        return self.contexts.get(channel, [])
    
    def add_context(self, channel: str, context_type: ContextType, context: Dict[str, Any]) -> None:
        if channel not in self.contexts:
            self.contexts[channel] = []
        id = str(uuid.uuid4())
        self.contexts[channel].append((id, context_type, context))
        self.save_contexts()

    def save_contexts(self) -> None:
        with self.lock:
            with open(self.path, "wb") as f:
                pickle.dump(self.contexts, f)

    def load_contexts(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, "rb") as f:
                self.contexts = pickle.load(f)
        else:
            self.contexts = {}