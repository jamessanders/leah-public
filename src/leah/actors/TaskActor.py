import json
import threading
import time
import traceback
from typing import List, Dict, Optional
from datetime import datetime
from leah.utils.PubSub import PubSub, Message
from leah.utils.Message import MessageType


class TaskActor:
    def __init__(self):
        """
        Initialize the TaskActor.
        """
        self._pubsub = PubSub.get_instance()
        self._tasks = []  # Dictionary to store tasks
        self._running = False
        self._thread = None
    
    def _handle_message(self, message: Message):
        print(" !! TaskActor: Handling message: " + str(message))
        task = json.loads(message.content)
        self._tasks.append(task)

    def _process_tasks(self):
        """
        Continuously process tasks that should be performed.
        This method runs in a separate thread.
        """
        self._running = True
        while self._running:
            # Process tasks that should be performed
            for task in list(self._tasks):
                try:    
                    when = task.get("when", None)
                    if when is None:
                        continue
                    when = datetime.strptime(when, "%Y-%m-%d %H:%M:%S")
                    if when < datetime.now():
                        print("Processing task: " + str(task))
                        who = task.get("who", None)
                        instructions = task.get("instructions", None)
                        instructions = "You wanted to do this task at " + when.strftime("%Y-%m-%d %H:%M:%S") + " \n\n" + instructions
                        via_channel = task.get("via_channel", None)
                        message = Message("@@task", via_channel, instructions, MessageType.DIRECT)
                        self._pubsub.publish(who, message)
                        self._tasks.remove(task)
                except Exception as e:
                    print("Error processing task: " + str(e))
                    traceback.print_exc()
            # Wait 1 second before the next iteration
            time.sleep(1)

    def listen(self):
        """
        List all tasks, optionally filtered by channel.
        
        Args:
            channel: Optional channel to filter tasks by
            
        Returns:
            List of task dictionaries
        """
        self._pubsub.subscribe("@@task", self._handle_message)
        
        # Start a new thread to process tasks
        self._thread = threading.Thread(target=self._process_tasks)
        self._thread.daemon = True  # Thread will exit when main program exits
        self._thread.start()

    def stop(self):
        """
        Stop the task processing thread.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish



