import time
from typing import Any, Dict, List
from leah.actions.IActions import IAction

class WaitAction(IAction):
    def __init__(self, config_manager, persona: str, query: str, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app

    def getTools(self) -> List[tuple]:
        return [
            (self.wait, "wait", "Wait for a specified number of seconds", {"wait_time": "number of seconds to wait"})
        ]

    def wait(self, arguments: Dict[str, Any]):
        yield ("system", self.persona + " is waiting for " + str(arguments.get("wait_time", 1)) + " seconds")
        wait_time = float(arguments.get("wait_time", 1))
        
        # if wait_time is less than 1 second, set it to 1 second
        if wait_time < 1:
            wait_time = 1

        # if wait_time is greater than 5 minutes, set it to 5 minutes
        if wait_time > 300:
            wait_time = 300

        time.sleep(wait_time)
        yield ("result", f"I have waited for {wait_time} seconds.") 