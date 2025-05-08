from datetime import datetime
from typing import List, Dict, Any
from leah.llm.ChatApp import ChatApp
from leah.actions.IActions import IAction
from leah.utils.PostOffice import Message, PostOffice

class EmailAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: ChatApp):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app

    def getTools(self) -> List[tuple]:
        return [
            (self.send_email,
             "send_email",
             "Send an email to a recipient. This is best for sending messages that can be responded to later. You can email agents or other personas.",
             {"body": "<body of the email>", "recipient": "<recipient of the email>"})
        ]

    def send_email(self, arguments: Dict[str, Any]):
        post_office = PostOffice.get_instance()
        body = arguments.get("body", "")    
        recipient = arguments.get("recipient", "")
        
        if not body or not recipient:
            yield ("end", "Body and recipient are required")
            return
        
        required_postfix = self.config_manager.get_user_id() + ".leah.com"
        users_address = self.config_manager.get_user_id() + "@leah.com"

        if not recipient.endswith(required_postfix) and not recipient == users_address:
            yield ("end", "Recipient must end with " + required_postfix + " or be the primary user's email address " + users_address)
            return

        # Create inboxes for both sender and recipient if they don't exist
        sender_inbox = self.persona + "@" + required_postfix
        recipient_inbox = recipient
        post_office.create_inbox(sender_inbox)
        post_office.create_inbox(recipient_inbox)

        post_office.send_message(
            return_inbox_id=recipient_inbox,
            body=body,
            chattapp=self.chat_app
        )
        yield ("system", f"Message sent to {recipient}")

    def additional_notes(self) -> str:
        users_address = self.config_manager.get_user_id() + "@leah.com"
        return f"""
    Important: Messages are sent within the system and can be used for asynchronous communication between different agents.
    The recipient will receive the message in their inbox and can respond when they are available.
    The primary user's email address is {users_address}
    """ 