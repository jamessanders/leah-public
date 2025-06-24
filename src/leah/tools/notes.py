from typing import List
from leah.config.LocalConfigManager import LocalConfigManager
from langchain_core.tools import tool

@tool
def put_note(note_name: str, note_content: str):
    """
    Put a note in the notes manager.
    """
    if not note_name or not note_content:
        return
    
    config_manager = LocalConfigManager("default")
    notes_manager = config_manager.get_notes_manager()
    notes_manager.put_note(note_name, note_content)
    return "Note added to the notes manager with name: " + note_name

@tool
def get_note(note_name: str):
    """
    Get a note from the notes manager.
    """
    if not note_name:
        return
    config_manager = LocalConfigManager("default")
    notes_manager = config_manager.get_notes_manager()
    return notes_manager.get_note(note_name)

@tool
def list_notes():
    """
    List all the notes in the notes manager.
    """
    config_manager = LocalConfigManager("default")
    notes_manager = config_manager.get_notes_manager()
    return ", ".join(notes_manager.get_all_notes())

@tool
def search_notes(terms: List[str]):
    """
    Search for notes in the notes manager.
    """
    if not terms:
        return
    
    config_manager = LocalConfigManager("default")
    notes_manager = config_manager.get_notes_manager()
    all_notes = notes_manager.get_all_notes()
    
    matching_notes = []
    for note in all_notes:
        if any(term.lower() in note.lower() for term in terms):
            matching_notes.append(note)
    
    if not matching_notes:
        return "No notes found matching the search terms: " + str(terms)
    else:
        return "Found the following matching notes: " + ", ".join(matching_notes)

