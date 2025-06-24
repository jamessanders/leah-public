from datetime import datetime
import json
from typing import Any, Dict, List
import uuid
from leah.actions.IActions import IAction
from leah.utils.Message import Message, MessageType
from leah.utils.PubSub import PubSub

class TaskAction(IAction):
    def __init__(self, config_manager, persona, query, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app

    def getTools(self):
        return [
           (self.schedule_task, 
             "schedule_task", 
             "Schedule a task for yourself for later, this can be used to remind yourself of a task at a later date, the date must be in the format %Y-%m-%d_%H-%M-%S.", 
             {
                 "when": "when the task should be scheduled for, must be in the format %Y-%m-%d %H:%M:%S.", 
                 "instructions": "Detailed instructions for the task"
             })
        ]

    def schedule_task(self, arguments: Dict[str, Any]):
        yield ("system", "Creating a new task")
        
        when = arguments.get("when", "")
        instructions = arguments.get("instructions", "")
        
        if not when or not instructions:
            yield ("end", "Task creation failed: when and instructions are required")
            return
            
        task_id = str(uuid.uuid4())
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pubsub = PubSub.get_instance()
        task_json = json.dumps({
            "when": when,
            "instructions": instructions,
            "who": "@" + self.persona,
            "via_channel": self.chat_app.channel_id
        })
        print(" !! TaskAction: Publishing task: " + task_json)
        pubsub.publish("@@task", Message("@@task", self.chat_app.channel_id, task_json, MessageType.DIRECT))
        yield ("result", f"Task created successfully and will be processed at {when}")
       
        