from datetime import datetime
from typing import Any, Dict
import uuid
from leah.actions.IActions import IAction
from leah.llm.LlmConnector import LlmConnector
from leah.utils.Message import Message
from leah.utils.PubSub import PubSub

class NotesAction(IAction): 
    def __init__(self, config_manager, persona, query, chat_app: Any):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app

    def getTools(self):
        return [
            (self.put_note, 
             "put_note", 
             "Add a note in your notes files, these can be used to answer the user's query. Note names should be in the format of 'note_name.note'", 
             {"note_name": "<the name of the note to add>", "note_content": "<the content of the note to add>"}),
            (self.put_note, 
             "update_note", 
             "Update a note in your notes files, these can be used to answer the user's query. Note names should be in the format of 'note_name.note'", 
             {"note_name": "<the name of the note to add>", "note_content": "<the content of the note to add>"}),
            (self.get_note,
              "get_note", 
              "Get a note from your notes, these can be used to answer the user's query. Note names should be in the format of 'note_name.note'", 
              {"note_name": "<the name of the note to get>"}),
            (self.get_note,
              "reference_note", 
              "Reference a note, these notes can be used to answer the user's query. Note names should be in the format of 'note_name.note'", 
              {"note_name": "<the name of the note to get>"}),
            (self.store_reminder, "store_reminder", "Store a reminder in your notes, this will be used to keep track of the users reminders", {"reminder": "<the reminder to store>", "when": "<when the reminder is for>"}),
            (self.get_reminders, "get_reminders", "Get all the reminders you have, this will be used to answer the user's queries about their reminders", {}),
            (self.remove_reminder, "remove_reminder", "Remove a reminder", {"id": "<the id of the reminder to remove>"}),
            (self.search_notes,
             "search_notes",
             "Search through note names for specific terms (comma-separated)",
             {"terms": "<comma-separated list of terms to search for in note names, e.g. 'meeting,todo,important'>"})
        ]

    def context_template(self, query: str, context: str, note_name: str) -> str:
        return f"""
I have looked up the note {note_name} and found the following information:

{context}

----
"""
    def schedule_task(self, arguments: Dict[str, Any]):
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("task_schedule")
        when = arguments.get("when","")
        task = arguments.get("task","")
        id = str(uuid.uuid4())
        if not when or not task:
            yield ("end", "Couldn't store task")
        if notes is None:
            notes = ""
        yield("system", f"Setting task for {when}, the task is {task}")
        task = f"{when} - Id: {id} - Task: {task}"
        notes_manager.put_note("task_schedule", task + "\n" + notes)
        yield ("end", "Task has been scheduled.")
        
    def store_reminder(self, arguments: Dict[str, Any]):
        yield ("system", "Storing reminder: " + arguments["reminder"] + " for " + arguments.get("when", "whenever"))
        id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("reminders")
        if notes is None:
            notes = ""
        notes_manager.put_note("reminders", "Reminder: " + arguments["reminder"] + ",When: " + arguments.get("when", "whenever") + ", Stored at: " + now + ", ID: " + id + "\n" + notes)
        yield ("end", "Stored a reminder: " + arguments["reminder"] + " for " + arguments.get("when", "whenever") + ".")

    def get_reminders(self, arguments: Dict[str, Any]):
        yield ("system", "Getting reminders")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        notes = notes_manager.get_note("reminders")
        if notes is None:
            yield ("result", self.context_template(self.query, "No reminders found", "reminders"))
        yield ("result", self.context_template(self.query, notes, "reminders"))

    def remove_reminder(self, arguments: Dict[str, Any]):
        yield ("system", "Removing reminder")
        id = arguments["id"]
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        reminders = notes_manager.get_note("reminders")
        keepers = []
        removed = False
        for line in reminders.split("\n"):
            if id in line:
                removed = True
                continue
            keepers.append(line)
        notes_manager.put_note("reminders", "\n".join(keepers))
        if removed:
            yield ("end", "Reminder removed")
        else:
            yield ("end", "Reminder not found")

    def put_note(self, arguments):
        from leah.llm.ChatApp import ChatApp
        name = arguments.get("note_name","")
        content = arguments.get("note_content","")
        if not name or not content:
            return
        
        yield ("system", "Putting note: " + name)
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        
        prev_contents = notes_manager.get_note(name)
        if not prev_contents:
            notes_manager.put_note(name, "Note added by " + self.persona + " at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n" + content + "\n----\n")
            pubsub = PubSub.get_instance()
            if self.chat_app.channel_id:
                pubsub.publish(self.chat_app.channel_id, Message("@" + self.persona, self.chat_app.channel_id, f"Created note: {name}"))
            yield ("result", f"I created a new note names {name}. ")
        else:
            chat_app = LlmConnector(self.config_manager, self.persona)
            new_contents = chat_app.query(f"Here are the contents of the note {name}: {prev_contents}\n\nPlease update the note with the following content, skip prose: {content}")
            if new_contents:
                content = new_contents
            notes_manager.put_note(name, prev_contents + "\n\nNote updated by " + self.persona + " at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n" + content + "\n----\n")
            pubsub = PubSub.get_instance()
            if self.chat_app.channel_id:
                pubsub.publish(self.chat_app.channel_id, Message("@" + self.persona, self.chat_app.channel_id, f"Updated note: {name}"))
            yield ("result", f"I have updated the note {name}. ")

    def get_note(self, arguments):
        yield ("system", "Getting note: " + arguments.get("note_name",""))
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", self.context_template(self.query, notes_manager.get_note(arguments.get("note_name","")), arguments.get("note_name", "")))

    def list_notes(self, arguments):
        yield ("system", "Listing notes")
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        yield ("result", "I have listed all the notes I have and the results are: " + str(", ".join(notes_manager.get_all_notes())))

    def search_notes(self, arguments):
        yield ("system", "Searching notes for terms: " + str(arguments.get("terms", "")))
        config_manager = self.config_manager
        notes_manager = config_manager.get_notes_manager()
        terms_string = arguments.get("terms", "")
        search_terms = [term.strip() for term in terms_string.split(",") if term.strip()]
        all_notes = notes_manager.get_all_notes()
        
        matching_notes = []
        for note in all_notes:
            if any(term.lower() in note.lower() for term in search_terms):
                matching_notes.append(note)
        
        if not matching_notes:
            yield ("result", "No notes found matching the search terms: " + str(search_terms))
        else:
            yield ("result", "Found the following matching notes: " + ", ".join(matching_notes))

    