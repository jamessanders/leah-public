from typing import List, Dict, Any
from leah.actions.IActions import IAction
from leah.utils.SubscriptionService import SubscriptionService
from leah.utils.PubSub import Message, PubSub
from leah.utils.TokenCounter import TokenCounter
import time
from datetime import datetime
import os
from langchain_core.tools import tool

def getTools(persona: str, config_manager):
    pubsub = PubSub()
    subscription_service = SubscriptionService()

    @tool
    def create_channel(name: str, members: str = ""):
        """
        Create a new channel and invite members to it. The creator will automatically be subscribed.
        """
        if not name:
            return "Channel name is required"

        if not name.startswith("#"):
            name = "#" + name

        # Create the channel by subscribing the creator (persona) first
        creator = "@" + persona
        subscription_service.subscribe(creator, name)
        subscription_service.make_admin(creator, name)

        # Process and invite members if provided
        if members:
            member_list = [m.strip() for m in members.split(",")]
            for member in member_list:
                if not member.startswith("@"):
                    member = "@" + member
                
                if not subscription_service.is_subscribed(member, name):
                    subscription_service.subscribe(member, name)
        
        # Create welcome message
        welcome_message = Message("@" + persona, name, f"Channel {name} has been created")
        welcome_message.set_to_channel()
        pubsub.publish(name, welcome_message)
        
        if members:
            return f"Successfully created channel {name} and invited: {members}"
        else:
            return f"Successfully created channel {name}"

    @tool
    def invite_member_to_channel(member: str, channel: str):
        """
        Invite a member to a specific channel. The member will be subscribed to the channel.
        """
        if not member:
            return "Member handle is required"
            
        if not channel:
            return "Channel is required"

        if channel.startswith("@"):
            return "I cannot invite to a direct message channel. Channel must not start with '@'"
            
        if "->" in channel:
            return "I cannot invite to a direct message channel. Channel must not contain '->'"

        if not channel.startswith("#"):
            channel = "#" + channel

        if not member.startswith("@"):
            member = "@" + member

        # If the member is already in the channel, don't invite them
        if subscription_service.is_subscribed(member, channel):
            return f"{member} is already a member of {channel}"

        subscription_service.subscribe(member, channel)
        
        return f"Successfully invited {member} to {channel}"

    @tool
    def kick_member_from_channel(member: str, channel: str):
        """
        Kick a member from a specific channel. The member will no longer receive messages from this channel.
        """
        if not member:
            return "Member handle is required"
            
        if not channel:
            return "Channel is required"

        if channel.startswith("@"):
            return "I cannot kick from a direct message channel. Channel must not start with '@'"

        if not channel.startswith("#"):
            channel = "#" + channel

        if not member.startswith("@"):
            member = "@" + member
        
        # Check if the member is actually in the channel
        if not subscription_service.is_subscribed(member, channel):
            return f"{member} is not a member of {channel}"

        subscription_service.unsubscribe(member, channel)
        
        # Notify about the kick
        kick_message = Message("@" + persona, channel, f"{member} has been kicked from the channel")
        kick_message.set_to_channel()
        pubsub.publish(channel, kick_message)
        
        return f"Successfully kicked {member} from {channel}"

    @tool
    def join_channel(channel: str):
        """
        Join a specific channel. You will receive messages from this channel.
        """
        if not channel:
            return "Channel is required"

        if channel.startswith("@"):
            return "I cannot join a direct message channel. Channel must not start with '@'"

        if not channel.startswith("#"):
            channel = "#" + channel

        member = "@" + persona
        
        if subscription_service.is_subscribed(member, channel):
            return f"I am already a member of {channel}"

        subscription_service.subscribe(member, channel)
        
        # Create join message
        join_message = Message("@" + persona, channel, f"{member} has joined the channel")
        join_message.set_to_channel()
        pubsub.publish(channel, join_message)
        
        return f"I have successfully joined the channel {channel}"

    @tool
    def leave_channel(channel: str):
        """
        Leave a specific channel. You will no longer receive messages from this channel.
        """
        if not channel:
            return "Channel is required"

        if channel.startswith("@"):
            return "I cannot leave a direct message channel. Channel must not start with '@'"

        if not channel.startswith("#"):
            channel = "#" + channel

        member = "@" + persona
        
        if not subscription_service.is_subscribed(member, channel):
            return f"{member} is not a member of {channel}"

        subscription_service.unsubscribe(member, channel)
        
        return f"Successfully left {channel}"

    @tool
    def get_channel_members(channel: str):
        """
        Get a list of all members in a specific channel.
        """
        if not channel:
            return "Channel is required"

        if channel.startswith("@"):
            return "I cannot get members from a direct message channel. Channel must not start with '@'"

        if not channel.startswith("#"):
            channel = "#" + channel
        
        members = subscription_service.get_channel_subscribers(channel)
        
        if not members:
            return f"I found no members in {channel}"
            
        members_list = ", ".join(members)
        return f"Members in {channel}: {members_list}"

    @tool
    def search_messages_in_channel(channel: str, terms: str):
        """
        Search for specific terms in a channel's message history.
        """
        terms_list = [term.strip().lower() for term in terms.split(",")]
        
        if not terms_list or terms_list == [""]:
            return "Please provide search terms as a comma-separated list"
            
        if not channel:
            return "Channel name is required"

        if channel.startswith("@"):
            return "I cannot search direct message channels. Channel must not start with '@'"

        if not channel.startswith("#"):
            channel = "#" + channel
        
        messages = pubsub.get_channel_messages(channel)
        found_messages = []
        
        for message in messages:
            content = message.content.lower()
            if any(term in content for term in terms_list):
                found_messages.append(message)
        
        if not found_messages:
            return f"I found no messages containing the terms: {', '.join(terms_list)}"

        # Sort messages by timestamp in descending order (most recent first)
        found_messages.sort(key=lambda x: float(x.sent_at) if x.sent_at else 0, reverse=False)
        
        # Initialize TokenCounter with a reasonable limit (4000 tokens)
        token_counter = TokenCounter(4000)
        
        # Create header with total matches found
        header = f"Found {len(found_messages)} matching messages in {channel} (showing most recent):\n"
        token_counter.feed(header)
        
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
                f"Message: {msg.content}\n"
                f"---\n"
            )
            token_counter.feed(message_block)
            
        # Get the chunks that fit within the token limit
        return "".join(token_counter.tail())

    @tool 
    def view_channel(channel: str):
        """
        View the messages in a specific channel.
        """
        if not channel:
            return "Channel name is required"

        if not channel.startswith("#") and not channel.startswith("@"):
            channel = "#" + channel
        
        messages = pubsub.get_channel_messages(channel)
        found_messages = []
        
        for message in messages:
            found_messages.append(message)
        
        if not found_messages:
            return f"No messages found in {channel}"

        # Sort messages by timestamp in descending order (most recent first)
        found_messages.sort(key=lambda x: float(x.sent_at) if x.sent_at else 0, reverse=False)
        
        # Initialize TokenCounter with a reasonable limit (4000 tokens)
        token_counter = TokenCounter(4000)
        
        # Create header with total matches found
        header = f"Found {len(found_messages)} matching messages in {channel} (showing most recent):\n"
        token_counter.feed(header)
        
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
                f"Message: {msg.content}\n"
                f"---\n"
            )
            token_counter.feed(message_block)
            
        # Get the chunks that fit within the token limit
        return "".join(token_counter.tail())

    @tool
    def check_direct_message_with(handle: str):
        """
        Look at the messages in a direct message channel with a specific user.
        """
        if not handle:
            return "User handle is required"
        
        if not handle.startswith("@"):
            handle = "@"+handle
        
        names = ["@" + persona, handle]
        names.sort()
        conversation_channel = "#" + names[0] + "->" + names[1]
        
        return view_channel(conversation_channel)

    def _transform_channel_name(channel):
        """Transform a channel name to its whiteboard key format."""
        if not channel:
            return ""
        
        # Remove # if present
        if channel.startswith("#"):
            channel = channel[1:]
            
        # Create a valid filename
        return f"whiteboard_channel_{channel}.txt"

    @tool
    def read_channel_whiteboard(channel: str):
        """
        Read the whiteboard content for a specific channel.
        """
        if not channel:
            return "Channel is required"

        if channel.startswith("@"):
            return "Cannot read whiteboard for a direct message channel. Channel must not start with '@'"

        whiteboard_file = _transform_channel_name(channel)
        whiteboard_path = config_manager.get_path(os.path.join("whiteboards", whiteboard_file))

        try:
            if not os.path.exists(whiteboard_path):
                return "Whiteboard is empty"
                
            with open(whiteboard_path, 'r') as f:
                content = f.read().strip()
                
            if not content:
                return "Whiteboard is empty"
                
            return f"Whiteboard content for {channel}:\n{content}"
        except Exception as e:
            return f"Error reading whiteboard: {str(e)}"

    @tool
    def update_channel_whiteboard(channel: str, content: str):
        """
        Update the whiteboard content for a specific channel.
        """
        if not channel:
            return "Channel is required"

        if not content:
            return "Content is required"

        if channel.startswith("@"):
            return "Cannot update whiteboard for a direct message channel. Channel must not start with '@'"

        whiteboard_file = _transform_channel_name(channel)
        whiteboard_path = config_manager.get_path(os.path.join("whiteboards", whiteboard_file))

        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(whiteboard_path), exist_ok=True)
            
            with open(whiteboard_path, 'r') as f:
                old_content = f.read()

            with open(whiteboard_path, 'w') as f:
                f.write(old_content + "\n\n@" + persona + " added:\n\n" + content)
            
            # Notify channel about the whiteboard update
            if not channel.startswith("#"):
                channel = "#" + channel
                
            update_message = Message("@" + persona, channel, f"@{persona} has updated the channel whiteboard.")
            update_message.set_to_channel()
            pubsub.publish(channel, update_message)
            
            return f"Successfully updated whiteboard for {channel}"
        except Exception as e:
            return f"Error updating whiteboard: {str(e)}"

    return [
        create_channel,
        invite_member_to_channel,
        kick_member_from_channel,
        join_channel,
        leave_channel,
        get_channel_members,
        search_messages_in_channel,
        view_channel,
        check_direct_message_with,
        read_channel_whiteboard,
        update_channel_whiteboard
    ]

