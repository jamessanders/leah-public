import os
from datetime import datetime
from datetime import timedelta
from leah.utils.LogItem import LogCollection
import re

class LogManager:
    def __init__(self, config_manager):
        """
        Initialize the LogManager with a LocalConfigManager instance.
        
        Args:
            config_manager (LocalConfigManager): The LocalConfigManager instance to use for path management
        """
        self.config_manager = config_manager
        self.logs_directory = self.config_manager.get_persona_path("logs")
        if not os.path.exists(self.logs_directory):
            os.makedirs(self.logs_directory, exist_ok=True)

    def log(self, message_type: str, message: str) -> None:
        """
        Log a tool message with a timestamp.
        
        Args:
            message_type (str): The type of message ('user' or 'assistant')
            message (str): The message content to log   
            persona (str): The persona name to organize logs under (default: "default")
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_entry = f"[{timestamp}] {message_type.upper()}: {message}\n"
        

        # Create a log file for the current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.logs_directory, f"system.log")
        
        # Append the log entry to the file
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(log_entry) 

    def log_index_item(self, term: str, message: str) -> None:
        """
        Log an index item with a timestamp.
        
        Args:
            term (str): The term to log
            message (str): The message to log
            persona (str): The persona name to organize logs under (default: "default")
        """
        # Sanitize the term by replacing special characters with underscores
        term = re.sub(r'[^a-zA-Z0-9]', '_', term.lower())
        # Remove consecutive underscores
        term = re.sub(r'_+', '_', term)
        # Remove leading/trailing underscores
        term = term.strip('_')
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        message = message.replace("\n", "\\n")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Create a log file for the current term in the logs/index/persona directory
        index_dir = os.path.join(self.logs_directory, "index")
        if not os.path.exists(index_dir):
            os.makedirs(index_dir, exist_ok=True)
        log_file = os.path.join(index_dir, f"{term}.log")
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(log_entry)
        
    def search_log_item(self, term: str) -> list[str]:
        """
        Search the log for an index item with a timestamp.
        """
        output = []
        term = term.strip().lower().replace(" ", "_")
        log_file = os.path.join(self.logs_directory, "index", f"{term}.log")
        print("Searching for log file: " + log_file)
        if not os.path.exists(log_file):
            return []
        with open(log_file, 'r', encoding='utf-8') as file:
            print("Found log file: " + log_file)
            for line in file:
                output.append(line.strip())
        return list(set(output))


    def log_chat(self, message_type: str, message: str) -> None:
        """
        Log a chat message with a timestamp.
        
        Args:
            message_type (str): The type of message ('user' or 'assistant')
            message (str): The message content to log
            persona (str): The persona name to organize logs under (default: "default")
        """
        if message_type not in ['user', 'assistant']:
            raise ValueError("message_type must be either 'user' or 'assistant'")
            
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        # Escape newlines in the message
        escaped_message = message.replace('\n', '\\n')
        log_entry = f"[{timestamp}] {message_type.upper()}: {escaped_message}\n"
        
        # Create persona-specific directory under logs/chat/
        chat_dir = os.path.join(self.logs_directory, "chat")
        if not os.path.exists(chat_dir):
            os.makedirs(chat_dir, exist_ok=True)
        
        # Create a log file for the current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(chat_dir, f"chat_{current_date}.log")
        
        # Append the log entry to the file
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(log_entry) 



    def get_all_indexes(self, persona: str) -> list[str]:
        """
        Get a list of all log file names in the logs/index directory without extensions.
        
        Returns:
            list[str]: A list of log file names without extensions.
        """
        index_dir = os.path.join(self.logs_directory, "index")
        if not os.path.exists(index_dir):
            return []
        log_files = []
        for root, _, files in os.walk(index_dir):
            for file in files:
                file_name, _ = os.path.splitext(file)
                log_files.append(file_name)
        return log_files 

    def get_logs_for_days(self, days: int) -> list[str]:
        """
        Get log files from the current date back to the specified number of days.

        Args:
            persona (str): The persona name to filter logs.
            days (int): The number of days to look back.

        Returns:
            list[str]: A list of log file paths.
        """
        log_entries = []
        chat_dir = os.path.join(self.logs_directory, "chat")
        if not os.path.exists(chat_dir):
            return log_entries

        current_date = datetime.now().date()
        for i in range(days + 1):
            date_to_check = current_date - timedelta(days=i)
            log_file = os.path.join(chat_dir, f"chat_{date_to_check.strftime('%Y-%m-%d')}.log")
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as file:
                    for line in file:
                        log_entries.append(" ".join(line.split(" ")[:200]))        
        log_collection = LogCollection.fromLogLines(log_entries)
        return log_collection.generate_report()

    def get_largest_index_logs(self, num_logs: int = 100) -> list[str]:
        """
        Get the largest index logs sorted from largest to smallest.

        Args:
            persona (str): The persona name to filter logs.
            num_logs (int): The number of log files to return (default: 100).

        Returns:
            list[str]: A list of the largest log file names without extensions, sorted by size.
        """
        index_dir = os.path.join(self.logs_directory, "index")
        if not os.path.exists(index_dir):
            return []

        log_files = []
        for root, _, files in os.walk(index_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                log_files.append((file, file_size))

        # Sort log files by size in descending order
        log_files.sort(key=lambda x: x[1], reverse=True)

        # Return the largest log file names without extensions, up to num_logs
        return [os.path.splitext(file)[0] for file, _ in log_files[:min(num_logs, len(log_files))]]
