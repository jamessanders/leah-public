from datetime import datetime
import json
from typing import Any, Dict, List
import uuid
from langchain_core.tools import tool
from leah.utils.Message import Message, MessageType
from leah.utils.PubSub import PubSub
from leah.config.LocalConfigManager import LocalConfigManager




def getTools(persona: str, channel_id: str):

    @tool
    def schedule_task(when: str, instructions: str):
        """
        Schedule a task for yourself for later, this can be used to remind yourself of a task at a later date.
        
        Args:
            when: when the task should be scheduled for, must be in the format %Y-%m-%d %H:%M:%S.
            instructions: Detailed instructions for the task
        """
        if not when or not instructions:
            return "Task creation failed: when and instructions are required"
        
        pubsub = PubSub.get_instance()
        task_json = json.dumps({
            "when": when,
            "instructions": instructions,
            "who": "@" + persona,
            "via_channel": channel_id
        })
        print(" !! TaskAction: Publishing task: " + task_json)
        pubsub.publish("@@task", Message("@@task", channel_id, task_json, MessageType.DIRECT))
        return f"Task created successfully and will be processed at {when}"
            
    return [schedule_task]