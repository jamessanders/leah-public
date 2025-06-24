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
from langchain_core.tools import tool


def getTools(persona: str, channel_id: str):
    pubsub = PubSub()

    @tool
    def check_messages(wait_time: int = 1):
        """
        Check for new messages on a channel.
        """
        channel = "@" + persona
        print ("MESSAGE ACTION: Checking messages on channel " + channel)
        
        if wait_time > 5:
            wait_time = 5

        sent_something = False
        result = ""
        try:
            for message in pubsub.watch(channel, wait_time):
                sent_something = True
                source = message.from_user
                if message.type == MessageType.DIRECT or message.type == MessageType.CHANNEL:
                    content = message.content
                    result += f"Message from {source}: {content}\n"
                elif message.type == MessageType.HANGUP:
                    break
            return result
        except Exception as e:
            print(e)

        if not sent_something:
            return "No new messages have arrived yet, check back later."


    @tool
    def send_direct_message(handle: str, message: str, wait: bool = False):
        """
        Send a direct message to a user.
        """
        my_handle = "@" + persona
        if not handle.startswith("@"):
            handle = "@" + handle
        shouldWait = wait
        if isinstance(shouldWait, str):
            shouldWait = shouldWait.lower() == "true"
        if not handle:
            return "I encountered an error sending a direct message: Handle is required."
        if not message:
            return "I encountered an error sending a direct message: Message is required."
        conversation_channel = CNG.get_direct_channel_name(handle, my_handle)
        subscription_service = SubscriptionService()
        subscription_service.subscribe(handle, conversation_channel)
        subscription_service.subscribe(my_handle, conversation_channel)
        if shouldWait:
            result = ""
            for message in pubsub.watch(conversation_channel, 60*10):
                if message.from_user == handle and not message.type == MessageType.HANGUP:
                    result += f"Message from {message.from_user}: {message.content}\n"
            return f"{my_handle} has finished sending a direct message to {handle}"
        else:
            pubsub.publish(conversation_channel, Message(my_handle, conversation_channel, message, MessageType.DIRECT))
            return f"I have sent a direct message to {handle} saying {message}. "

    @tool
    def send_message(channel: str, message: str):
        """
        Send a message to a channel.
        """
        
        if not channel:
            return "I encountered an error sending a message: Channel is required."
            
        if not message:
            return "I encountered an error sending a message: Message content is required."

        subscription_service = SubscriptionService()
        send_message = None
        sender_channel = "@"+persona
        receiver_channel = channel

        if channel.startswith("@"):
            conversation_channel = CNG.get_direct_channel_name(sender_channel, receiver_channel)
            subscription_service.subscribe(sender_channel, conversation_channel)
            subscription_service.subscribe(receiver_channel, conversation_channel)
            send_message = Message(sender_channel, conversation_channel, message)
            send_message.set_to_direct()
        else:
            conversation_channel = channel
            send_message = Message(sender_channel, conversation_channel, message)
            send_message.set_to_channel()

        # Publish the message with source information
        print(f"MESSAGE ACTION: Publishing message to channel {conversation_channel} from {persona}: {message}")
        pubsub.publish(conversation_channel, send_message)
        
        if send_message.is_direct():
            return f"I have sent a direct message to {channel} saying {message}. "
        else:
            return f"I have sent a message to {channel} saying {message}. "

    @tool
    def search_messages(terms: List[str], channel: str = "@" + persona):
        """
        Search for messages in a channel.
        """
        terms = [term.strip().lower() for term in terms]
        
        if not terms or terms == [""]:
            return "Please provide search terms as a comma-separated list"
            
        messages = pubsub.get_channel_messages(channel)
        found_messages = []
        
        for message in messages:
            content = message.content.lower()
            if any(term in content for term in terms):
                found_messages.append(message)
        
        if not found_messages:
            return f"No messages found containing the terms: {', '.join(terms)}"

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
            
        return "".join(token_counter.tail())

    return [check_messages, send_direct_message, send_message, search_messages]