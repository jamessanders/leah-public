import os

class NotesManager:
    def __init__(self, config_manager):
        """
        Initialize the NotesManager with a LocalConfigManager instance.
        
        Args:
            config_manager (LocalConfigManager): The LocalConfigManager instance to use for path management
        """
        self.config_manager = config_manager
        self.notes_directory = self.config_manager.get_path("notes")
        if not os.path.exists(self.notes_directory):
            os.makedirs(self.notes_directory, exist_ok=True)
        # Create backup directory within notes directory
        self.backup_directory = os.path.join(self.notes_directory, "backup")
        if not os.path.exists(self.backup_directory):
            os.makedirs(self.backup_directory, exist_ok=True)
        self.memories_directory = os.path.join(self.notes_directory, "memories")
        if not os.path.exists(self.memories_directory):
            os.makedirs(self.memories_directory, exist_ok=True)
        if not os.path.exists(os.path.join(self.backup_directory, "memories")):
            os.makedirs(os.path.join(self.backup_directory, "memories"), exist_ok=True)

    def get_note(self, note_name: str) -> str:
        """Retrieve the content of a specific note file."""
        if not note_name.endswith(".note"):
            note_name += ".note"
        note_path = os.path.join(self.notes_directory, note_name)
        if os.path.exists(note_path):
            with open(note_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            return None

    def put_note(self, note_name: str, content: str) -> None:
        """Store content into a specific note file."""
        # Check if note exists and create backup if it does
        note_name = os.path.basename(note_name).strip()
        if not note_name.endswith(".note"):
            note_name += ".note"
        note_path = os.path.join(self.notes_directory, note_name)
        if os.path.exists(note_path):
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            backup_name = f"{os.path.splitext(note_name)[0]}_{timestamp}.note"
            backup_path = os.path.join(self.backup_directory, backup_name)
            with open(note_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        with open(note_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def get_all_notes(self) -> list[str]:
        """Retrieve the names of all note files."""
        return [note_name for note_name in os.listdir(self.notes_directory) if note_name.endswith(".note")]

    def get_all_notes_content(self) -> str:
        """Retrieve the content of all note files and output them as a single string."""
        all_content = []
        for note_name in os.listdir(self.notes_directory):
            note_path = os.path.join(self.notes_directory, note_name)
            if (not note_path.endswith(".txt")):
                continue
            if os.path.isfile(note_path):
                with open(note_path, 'r', encoding='utf-8') as file:
                    print("Note: ", note_name)
                    all_content.append(note_name + ":\n" + file.read())
        return "\n".join(all_content)

    def get_notes_by_size(self, max_notes: int = None) -> list[str]:
        """Retrieve the filenames of all note files ordered by size from largest to smallest, with extensions.
        Optionally limit the number of notes returned."""
        notes_with_size = []
        for note_name in os.listdir(self.notes_directory):
            note_path = os.path.join(self.notes_directory, note_name)
            if note_name.endswith(".txt") and os.path.isfile(note_path):
                notes_with_size.append((note_name, os.path.getsize(note_path)))
        # Sort notes by size in descending order
        notes_with_size.sort(key=lambda x: x[1], reverse=True)
        # Return filenames with extensions, limited by max_notes if provided
        return [note[0] for note in notes_with_size[:max_notes]] 
    