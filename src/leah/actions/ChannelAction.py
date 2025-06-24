from typing import List, Dict, Any
from leah.actions.IActions import IAction
from leah.utils.SubscriptionService import SubscriptionService
from leah.utils.PubSub import Message, PubSub
from leah.utils.TokenCounter import TokenCounter
import time
from datetime import datetime
import os

class ChannelAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.pubsub = PubSub()

    def getTools(self) -> List[tuple]:
        return [
            (self.create_channel,
             "create",
             "Create a new channel and invite members to it. The creator will automatically be subscribed.",
             {"name": "<name of the channel to create>", "members": "<comma-separated list of members to invite>"}),
            (self.invite_member,
             "invite",
             "Invite a member to a specific channel. The member will be subscribed to the channel.",
             {"member": "<the handle of the member to invite>", "channel": "<the channel to invite the member to>"}),
            (self.kick_member,
             "kick",
             "Kick a member from a specific channel. The member will no longer receive messages from this channel.",
             {"member": "<the handle of the member to kick>", "channel": "<the channel to kick the member from>"}),
            (self.join_channel,
             "join",
             "Join a specific channel. You will receive messages from this channel.",
             {"channel": "<the channel to join>"}),
            (self.leave_channel,
             "leave",
             "Leave a specific channel. You will no longer receive messages from this channel.",
             {"channel": "<the channel to leave>"}),
            (self.get_channel_members,
             "members",
             "Get a list of all members in a specific channel.",
             {"channel": "<the channel to get members from>"}),
            (self.search_messages,
             "search",
             "Search for specific terms in a channel's message history.",
             {"channel": "<the channel to search in>", "terms": "<comma-separated list of terms to search for>"}),
            (self.view_channel,
             "view",
             "View the messages in a specific channel.",
             {"channel": "<the channel to view>"}),
            (self.view_channel,
             "check_channel",
             "Look at the messages in a specific channel.",
             {"channel": "<the channel to check>"}),
            (self.check_direct_message_with,
             "check_direct_message_with_user",
             "Look at the messages in a specific channel.",
             {"handle": "<the handle of the user to check direct messages with>"}),
        ]

    def invite_member(self, arguments: Dict[str, Any]):
        member = arguments.get("member", "")
        channel = arguments.get("channel", "")
        
        if not member:
            yield ("result", "Member handle is required")
            return
            
        if not channel:
            yield ("result", "Channel is required")
            return

        if channel.startswith("@"):
            yield ("result", "I cannot invite to a direct message channel. Channel must not start with '@'")
            return
        if "->" in channel:
            yield ("result", "I cannot invite to a direct message channel. Channel must not contain '->'")
            return

        if not channel.startswith("#"):
            channel = "#" + channel

        if not member.startswith("@"):
            member = "@" + member

        ## if the member is already in the channel, don't invite them
        subscription_service = SubscriptionService()
        if subscription_service.is_subscribed(member, channel):
            yield ("result", f"{member} is already a member of {channel}")
            return

        subscription_service.subscribe(member, channel)
        
        yield ("system", f"{self.persona} invited {member} to channel {channel}")
        yield ("result", f"Successfully invited {member} to {channel}")

    def kick_member(self, arguments: Dict[str, Any]):
        member = arguments.get("member", "")
        channel = arguments.get("channel", "")
        
        if not member:
            yield ("result", "Member handle is required")
            return
            
        if not channel:
            yield ("result", "Channel is required")
            return

        if channel.startswith("@"):
            yield ("result", "I cannot kick from a direct message channel. Channel must not start with '@'")
            return

        if not channel.startswith("#"):
            channel = "#" + channel

        if not member.startswith("@"):
            member = "@" + member

        subscription_service = SubscriptionService()
        
        # Check if the member is actually in the channel
        if not subscription_service.is_subscribed(member, channel):
            yield ("result", f"{member} is not a member of {channel}")
            return

        subscription_service.unsubscribe(member, channel)
        
        # Notify about the kick
        kick_message = Message("@" + self.persona, channel, f"{member} has been kicked from the channel")
        kick_message.set_to_channel()
        self.pubsub.publish(channel, kick_message)
        
        yield ("system", f"{self.persona} kicked {member} from channel {channel}")
        yield ("result", f"Successfully kicked {member} from {channel}")

    def leave_channel(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        
        if not channel:
            yield ("result", "Channel is required")
            return

        if channel.startswith("@"):
            yield ("result", "I cannot leave a direct message channel. Channel must not start with '@'")
            return

        if not channel.startswith("#"):
            channel = "#" + channel

        member = "@" + self.persona
        subscription_service = SubscriptionService()
        
        if not subscription_service.is_subscribed(member, channel):
            yield ("result", f"{member} is not a member of {channel}")
            return

        subscription_service.unsubscribe(member, channel)
        
        yield ("system", f"{self.persona} left channel {channel}")
        yield ("result", f"Successfully left {channel}")

    def create_channel(self, arguments: Dict[str, Any]):
        name = arguments.get("name", "")
        members = arguments.get("members", "")
        
        if not name:
            yield ("result", "Channel name is required")
            return

        if not name.startswith("#"):
            name = "#" + name

        # Create the channel by subscribing the creator (persona) first
        creator = "@" + self.persona
        subscription_service = SubscriptionService()
        subscription_service.subscribe(creator, name)
        subscription_service.make_admin(creator, name)

        # Process and invite members if provided
        if members:
            member_list = [m.strip() for m in members.split(",")]
            for member in member_list:
                if not member.startswith("@"):
                    member = "@" + member
                
                if not subscription_service.is_subscribed(member, name):
                    yield ("system", f"{self.persona} invited {member} to channel {name}")
                    subscription_service.subscribe(member, name)
        
        # Create welcome message
        welcome_message = Message("@" + self.persona, name, f"Channel {name} has been created")
        welcome_message.set_to_channel()
        self.pubsub.publish(name, welcome_message)
        
        yield ("system", f"{self.persona} created channel {name}")
        if members:
            yield ("result", f"Successfully created channel {name} and invited: {members}")
        else:
            yield ("result", f"Successfully created channel {name}")

    def get_channel_members(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        
        if not channel:
            yield ("result", "Channel is required")
            return

        if channel.startswith("@"):
            yield ("result", "I cannot get members from a direct message channel. Channel must not start with '@'")
            return

        if not channel.startswith("#"):
            channel = "#" + channel
        
        yield ("system", f"Getting members for {channel}")
        
        subscription_service = SubscriptionService()
        members = subscription_service.get_channel_subscribers(channel)
        
        if not members:
            yield ("result", f"I found no members in {channel}")
            return
            
        members_list = ", ".join(members)
        yield ("result", f"Members in {channel}: {members_list}")

    def search_messages(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        terms = arguments.get("terms", "").split(",")
        terms = [term.strip().lower() for term in terms]
        
        if not terms or terms == [""]:
            yield ("result", "Please provide search terms as a comma-separated list")
            return
            
        if not channel:
            yield ("result", "Channel name is required")
            return

        if channel.startswith("@"):
            yield ("result", "I cannot search direct message channels. Channel must not start with '@'")
            return

        if not channel.startswith("#"):
            channel = "#" + channel
            
        yield ("system", f"Searching for terms {', '.join(terms)} in channel {channel}")
        
        messages = self.pubsub.get_channel_messages(channel)
        found_messages = []
        
        for message in messages:
            content = message.content.lower()
            if any(term in content for term in terms):
                found_messages.append(message)
        
        if not found_messages:
            yield ("result", f"I found no messages containing the terms: {', '.join(terms)}")
            return

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
        yield ("result", "".join(token_counter.tail()))

    def check_direct_message_with(self, arguments: Dict[str, Any]):
        handle = arguments.get("handle", "")
        if not handle:
            yield ("result", "User handle is required")
            return
        
        if not handle.startswith("@"):
            handle = "@"+handle
        
        names = ["@" + self.persona, handle]
        names.sort()
        conversation_channel = "#" + names[0] + "->" + names[1]
        
        yield from self.view_channel({"channel": conversation_channel})

    def view_channel(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
            
        if not channel:
            yield ("result", "Channel name is required")
            return


        if not channel.startswith("#") and not channel.startswith("@"):
            channel = "#" + channel
            

        yield ("system", f"Viewing channel {channel}")
        
        messages = self.pubsub.get_channel_messages(channel)
        found_messages = []
        
        for message in messages:
            found_messages.append(message)
        
        if not found_messages:
            yield ("result", f"No messages found in {channel}")
            return

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
        yield ("result", "".join(token_counter.tail()))


    def _transform_channel_name(self, channel: str) -> str:
        """Transform a channel name to its whiteboard key format."""
        if not channel:
            return ""
        
        # Remove # if present
        if channel.startswith("#"):
            channel = channel[1:]
            
        # Create a valid filename
        return f"whiteboard_channel_{channel}.txt"

    def read_channel_whiteboard(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        
        if not channel:
            yield ("result", "Channel is required")
            return

        if channel.startswith("@"):
            yield ("result", "Cannot read whiteboard for a direct message channel. Channel must not start with '@'")
            return

        whiteboard_file = self._transform_channel_name(channel)
        whiteboard_path = self.config_manager.get_path(os.path.join("whiteboards", whiteboard_file))
        
        print(f"Reading whiteboard for {channel}")

        try:
            if not os.path.exists(whiteboard_path):
                yield ("result", "Whiteboard is empty")
                return
                
            with open(whiteboard_path, 'r') as f:
                content = f.read().strip()
                
            if not content:
                yield ("result", "Whiteboard is empty")
                return
                
            yield ("result", f"Whiteboard content for {channel}:\n{content}")
        except Exception as e:
            yield ("error", f"Error reading whiteboard: {str(e)}")

    def update_channel_whiteboard(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        content = arguments.get("content", "")
        
        if not channel:
            yield ("result", "Channel is required")
            return

        if not content:
            yield ("result", "Content is required")
            return

        if channel.startswith("@"):
            yield ("result", "Cannot update whiteboard for a direct message channel. Channel must not start with '@'")
            return

        whiteboard_file = self._transform_channel_name(channel)
        whiteboard_path = self.config_manager.get_path(os.path.join("whiteboards", whiteboard_file))
        
        yield ("system", f"Updating whiteboard for {channel}")

        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(whiteboard_path), exist_ok=True)
            
            with open(whiteboard_path, 'r') as f:
                old_content = f.read()

            with open(whiteboard_path, 'w') as f:
                f.write(old_content + "\n\n@" + self.persona + " added:\n\n" + content)
            
            # Notify channel about the whiteboard update
            if not channel.startswith("#"):
                channel = "#" + channel
                
            update_message = Message("@" + self.persona, channel, f"@{self.persona} has updated the channel whiteboard.")
            update_message.set_to_channel()
            self.pubsub.publish(channel, update_message)
            
            yield ("result", f"Successfully updated whiteboard for {channel}")
        except Exception as e:
            yield ("error", f"Error updating whiteboard: {str(e)}")

    def additional_notes(self) -> str:
        return """
    Important information about channel management: 
    
        - Channels are identified by the '#' prefix
        - Members must be subscribed to a channel to receive messages
        - Members can be invited, kicked, or leave channels
    """

    def join_channel(self, arguments: Dict[str, Any]):
        channel = arguments.get("channel", "")
        
        if not channel:
            yield ("result", "Channel is required")
            return

        if channel.startswith("@"):
            yield ("result", "I cannot join a direct message channel. Channel must not start with '@'")
            return

        if not channel.startswith("#"):
            channel = "#" + channel

        member = "@" + self.persona
        subscription_service = SubscriptionService()
        
        if subscription_service.is_subscribed(member, channel):
            yield ("result", f"I am already a member of {channel}")
            return

        subscription_service.subscribe(member, channel)
        
        # Create join message
        join_message = Message("@" + self.persona, channel, f"{member} has joined the channel")
        join_message.set_to_channel()
        self.pubsub.publish(channel, join_message)
        
        yield ("system", f"{self.persona} joined channel {channel}")
        yield ("result", f"I have successfully joined the channel {channel}") 