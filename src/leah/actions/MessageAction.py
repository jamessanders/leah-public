from typing import List, Dict, Any
import uuid
from leah.actions.IActions import IAction
from leah.utils.Message import MessageType
from leah.utils.SubscriptionService import SubscriptionService
from leah.utils.PubSub import Message, PubSub
from leah.utils.TokenCounter import TokenCounter
import leah.utils.ChannelNameGuide as CNG
import time
from datetime import datetime

class MessageAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.threading = False
        self.pubsub = PubSub()

    def getTools(self) -> List[tuple]:
        return [
            (self.send_message,
             "send_message",
             "Send a message to a specific channel. The message will be delivered to all members of that channel.",
             {"channel": "<the channel to send the message to>", "message": "<the message content to send>"}),
            (self.send_message,
             "post_message",
             "Post a message to a specific channel. The message will be delivered to all members of that channel.",
             {"channel": "<the channel to send the message to>", "message": "<the message content to send>"}),
             (self.send_message,
             "send_channel_message",
             "Send a message to a specific channel. The message will be delivered to any listeners on that channel.",
             {"channel": "<the channel to send the message to>", "message": "<the message content to send>"}),
             (self.send_direct_message,
             "send_direct_message",
             "Send a message to a specific user. The message will be delivered to the user directly.  If you want to wait for a response from the user, set the wait parameter to true. You should wait for responses from agents.",
             {"handle": "<the handle of the user to send the message to>", "message": "<the message content to send>", "wait": "<wait for a response from the user (true or false)>"}),
             (self.search_messages,
             "search_messages",
             "Search for specific terms in messages your message history.",
             {"terms": "<comma-separated list of terms to search for>"})
        ]

    def check_messages(self, arguments: Dict[str, Any]):
        wait_time = int(arguments.get("wait_time", 1))
        channel = arguments.get("channel", "@" + self.persona)
        print ("MESSAGE ACTION: Checking messages on channel " + channel)
        yield ("system", f"{self.persona} is checking channel {channel} for new messages...waiting {wait_time} seconds")
        
        if wait_time > 5:
            wait_time = 5

        sent_something = False
        result = ""
        try:
            for message in self.pubsub.watch(channel, wait_time):
                sent_something = True
                source = message.from_user
                if message.type == MessageType.DIRECT or message.type == MessageType.CHANNEL:
                    content = message.content
                    yield ("system", f"{self.persona}: Found a new message from {source}...")
                    result += f"Message from {source}: {content}\n"
                elif message.type == MessageType.SYSTEM:
                    yield ("system", message.content)
                elif message.type == MessageType.HANGUP:
                    yield ("system", "HANGUP")
                    break
            yield ("result", result)
        except Exception as e:
            print(e)

        if not sent_something:
            yield ("result", "No new messages have arrived yet, check back later.")


    def call_user(self, arguments: Dict[str, Any]):
        handle = arguments.get("handle", "")
        message = arguments.get("message", "")

        yield ("system", f"{self.persona} is calling {handle}: {message}")


        conversation_channel = "#$" + str(uuid.uuid4())
        subscription_service = SubscriptionService()
        subscription_service.subscribe(handle, conversation_channel)
        subscription_service.subscribe("@" + self.persona, conversation_channel)
        subscription_service.make_admin(handle, conversation_channel)
        pubsub = PubSub()
        pubsub.publish(conversation_channel, Message(self.persona, conversation_channel, message, MessageType.CHANNEL))

        result = ""
        for message in self.pubsub.watch(conversation_channel, 60*10):
            if message.type == MessageType.DIRECT or message.type == MessageType.CHANNEL:
                result += f"Message from {message.from_user}: {message.content}\n"
                pubsub.publish(self.chat_app.channel_id, Message(self.persona, self.chat_app.channel_id, message.content))
            elif message.type == MessageType.SYSTEM:
                yield ("system", message.content)
            elif message.type == MessageType.HANGUP:
                break

        yield("result", "User has hung up the call.")
        yield ("system", f"{self.persona} has finished calling {handle}")
        subscription_service.unsubscribe(handle, conversation_channel)
        subscription_service.unsubscribe("@" + self.persona, conversation_channel)

        yield ("result", result)

    def send_direct_message(self, arguments: Dict[str, Any]):
        handle = arguments.get("handle", "")
        message = arguments.get("message", "")
        shouldWait = arguments.get("wait", False)
        if isinstance(shouldWait, str):
            shouldWait = shouldWait.lower() == "true"
        if not handle:
            yield ("response", "I encontered an error sending a direct message: Handle is required.")
            return
        if not message:
            yield ("response", "I encontered an error sending a direct message: Message is required.")
            return
        if not handle.startswith("@"):
            handle = "@" + handle
        yield from self.send_message({"channel": handle, "message": message})
        if shouldWait:
            result = ""
            conversation_channel = CNG.get_direct_channel_name(handle, "@"+self.persona)
            for message in self.pubsub.watch(conversation_channel, 60*10):
                yield ("system", f"{self.persona} is waiting for a response from {conversation_channel}...")
                if message.from_user == handle and not message.type == MessageType.HANGUP:
                    result += f"Message from {message.from_user}: {message.content}\n"
            yield ("system", f"{self.persona} has finished sending a direct message to {handle}")
            yield ("result", result)

    def send_message(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        message = arguments.get("message", "")
        
        if not channel:
            yield ("response", "I encontered an error sending a message: Channel is required.")
            return
            
        if not message:
            yield ("response", "I encontered an error sending a message: Message content is required.")
            return

        subscription_service = SubscriptionService()
        send_message = None
        sender_channel = "@"+self.persona
        receiver_channel = channel

        if channel.startswith("@"):
            conversation_channel = CNG.get_direct_channel_name(sender_channel, receiver_channel)
            subscription_service.subscribe(sender_channel, conversation_channel)
            subscription_service.subscribe(receiver_channel, conversation_channel)
            yield ("system", f"{self.persona} sent a direct message to {channel}: {message}")
            send_message = Message(sender_channel, conversation_channel, message)
            send_message.set_to_direct()
        else:
            conversation_channel = channel
            yield ("system", f"{self.persona} sent a message to channel {channel}: {message}")
            send_message = Message(sender_channel, conversation_channel, message)
            send_message.set_to_channel()

        # Publish the message with source information
        print(f"MESSAGE ACTION: Publishing message to channel {conversation_channel} from {self.persona}: {message}")
        self.pubsub.publish(conversation_channel, send_message)
        
        if send_message.is_direct():
            yield ("result", f"I have sent a direct message to {channel} saying {message}. ")
        else:
            yield ("result", f"I have sent a message to {channel} saying {message}. ")

    def search_messages(self, arguments: Dict[str, Any]):
        terms = arguments.get("terms", "").split(",")
        terms = [term.strip().lower() for term in terms]
        
        if not terms or terms == [""]:
            yield ("error", "Please provide search terms as a comma-separated list")
            return
            
        channel = arguments.get("channel", "@" + self.persona)
        
        yield ("system", f"Searching for terms {', '.join(terms)} in channel {channel}")
        
        messages = self.pubsub.get_channel_messages(channel)
        found_messages = []
        
        for message in messages:
            content = message.content.lower()
            if any(term in content for term in terms):
                found_messages.append(message)
        
        if not found_messages:
            yield ("result", f"No messages found containing the terms: {', '.join(terms)}")
            return

        # Sort messages by timestamp in descending order (most recent first)
        found_messages.sort(key=lambda x: float(x.sent_at) if x.sent_at else 0, reverse=True)
        
        # Initialize TokenCounter with a reasonable limit (4000 tokens)
        token_counter = TokenCounter(4000)
        
        # Process messages and add to token counter
        for msg in found_messages:
            try:
                date_obj = datetime.fromtimestamp(float(msg.sent_at))
                formatted_date = date_obj.strftime("%B %d, %Y at %I:%M:%S %p")
            except (ValueError, TypeError):
                formatted_date = str(msg.sent_at)
                
            message_block = (
                f"From: {msg.from_user}\n"
                f"Time: {formatted_date}\n"
                f"Channel: {msg.via_channel}\n"
                f"Message: {msg.content}\n"
                f"---\n"
            )
            token_counter.feed(message_block)
            
        # Get the chunks that fit within the token limit
        result_chunks = token_counter.tail()
        
        token_counter.feed(f"I found {len(found_messages)} matching messages (showing {len(result_chunks)} most recent):\n")
            
        yield ("result", "".join(token_counter.tail()))
        yield ("end", "Search complete")

   