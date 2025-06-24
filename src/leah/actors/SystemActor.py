from typing import List
from leah.utils.PubSub import PubSub, Message
from leah.utils.Message import MessageType
import threading

from leah.utils.SubscriptionService import SubscriptionService

class SystemActor:
    def __init__(self):
        self._pubsub = PubSub.get_instance()
        self._running = False
        self._thread = None

    def _handle_system_messages(self, message: Message):
        # Forward each system message as a channel action to #system-chan
        if message.type == MessageType.SYSTEM:
            # Forward the system message as a channel action to #system-chan
            channel_action_message = Message(
                from_user="@sys",
                via_channel="#system-chan",
                content=message.content,
                type=MessageType.CHANNEL
            )
            self._pubsub.publish("#system-chan", channel_action_message)

    def listen(self):
        # Subscribe to the #system channel for system messages
        subscription_service = SubscriptionService.get_instance()
        subscription_service.subscribe("@sys", "#system")
        self._pubsub.subscribe("@sys", self._handle_system_messages)
        # Optionally, run in a background thread if needed for future expansion
