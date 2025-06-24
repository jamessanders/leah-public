from datetime import datetime
import os
from pathlib import Path
from leah.utils.DirectiveManager import DirectiveManager
from leah.utils.NotesManager import NotesManager
from leah.utils.LogManager import LogManager
from leah.utils.FileManager import FileManager
from leah.config.GlobalConfig import GlobalConfig
from leah.actions.webdriver_singleton import WebDriverSingleton  
from selenium.webdriver.remote.webdriver import WebDriver
from leah.utils.PostOffice import PostOffice

class LocalConfigManager:
    def __init__(self, user_id: str, persona="default"):
        """
        Initialize the LocalConfigManager with a user ID.
        
        Args:
            user_id (str): The user ID to create a config directory for
        """
        self.user_id = user_id
        self.base_dir = os.path.expanduser(f'~/.leah/{user_id}')
        self.persona = persona
        self.directive_manager = DirectiveManager(self)

        
        # Create the directory structure if it doesn't exist
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
    
    def get_http_path(self, filename: str) -> str:
        """
        Get the full path for a file under the user's config directory.
        
        Args:
            filename (str): The name of the file to get the path for
        """
        return "/"+self.user_id + "/" + filename

    def get_path(self, filename: str) -> str:
        """
        Get the full path for a file under the user's config directory.
        
        Args:
            filename (str): The name of the file to get the path for
            
        Returns:
            str: The full path to the file
        """
        return os.path.join(self.base_dir, filename)
    
    def get_home_config_directory(self) -> str:
        """Get the path to the home config directory."""
        return self.base_dir

    def get_persona_config_directory(self) -> str:
        """Get the path to the persona config directory."""
        return os.path.join(self.base_dir, self.persona)

    def get_persona_path(self, filename:str) -> str:
        return os.path.join(os.path.join(self.base_dir, self.persona), filename)
    
    def get_sandbox_directory_path(self) -> str:
        sandbox = os.path.join(os.path.join(self.base_dir, self.persona), "sandbox")
        if not os.path.exists(sandbox):
            os.makedirs(sandbox, exist_ok=True)
        return sandbox

    def get_agent_descriptions(self) -> dict:
        return ""
        output = "Agent Directory: \n\n"
        for persona, description in self.get_config().get_agent_descriptions().items():
            if persona != self.persona:
                output += f"    @{persona} - {description}\n"
        return output + """
     
    Important information regarding agents: 
    
        - Agents have capabilities that you may not have like using tools, getting information from other sources and so on, you should always ask an agent if you are not sure how to perform a task.
        - You can either directly message an agent or invite them to a channel
        - After you invite an agent to the channel, you can query them by using the @handle of the agent in the channel.
        - Do not assume agents have any knowledge of the user or other agents.  
        - Agents can run a variety of tools you may not be aware of, so be sure to ask one if you need to use a tool that is not listed in the tools you have available.

"""

    def get_system_content(self, persona='default') -> str:
            """Get the system content based on the specified persona."""
            persona_config = self.get_config()._get_persona_config(persona)
            directives_str = ""
            if persona_config.get('directives', []):
                directives = []
                for directive in persona_config.get('directives', []):
                    if self.directive_manager.get_directive_by_name(directive):
                        directives.append(self.directive_manager.get_directive_by_name(directive))
                    else:
                        print(f"Directive {directive} not found")
                directives_str = "\n".join(directives)
            else:
                traits = []
                for trait in persona_config.get('traits', []):
                    traits.append(f"- {trait}")
                directives_str = "\n".join(traits)
            
            global_directive = self.directive_manager.get_directive_by_name("_global")
            
            agent_descriptions = self.get_agent_descriptions()

            user_time_str = "The users current time and date is " + datetime.now().strftime("%I:%M %p on %A, %B %d %Y")

            return f"""
    Hello, this is a description of who you are: 

    {persona_config['description']}.

    {directives_str}

    {global_directive}

    {user_time_str}

    {agent_descriptions}
    """

    
    def ensure_file_exists(self, filename: str) -> None:
        """
        Ensure that a file exists in the config directory, creating it if necessary.
        
        Args:
            filename (str): The name of the file to ensure exists
        """
        file_path = self.get_path(filename)
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                pass  # Create empty file
                
    def get_notes_manager(self) -> NotesManager:
        """
        Get a NotesManager instance for managing notes.
        
        Returns:
            NotesManager: A NotesManager instance configured for this user
        """
        return NotesManager(self)
        
    def get_log_manager(self) -> LogManager:
        """
        Get a LogManager instance for managing logs.
        
        Returns:
            LogManager: A LogManager instance configured for this user
        """
        return LogManager(self) 
    
    def get_config(self) -> GlobalConfig:
        """
        Get a Config instance for managing configuration.
        
        Returns:
            Config: A Config instance configured for this user
        """
        return GlobalConfig()
    
    def get_web_driver(self) -> WebDriver:
        """
        Get a WebDriver instance for managing web drivers.
        
        Returns:
            WebDriver: A WebDriver instance configured for this user
        """
        return WebDriverSingleton().get_driver()

    def get_file_manager(self) -> FileManager:
        """
        Get a FileManager instance for managing files.
        
        Returns:
            FileManager: A FileManager instance configured for this user
        """
        return FileManager(self)

    def get_post_office(self) -> PostOffice:
        """
        Get the singleton PostOffice instance.
        
        Returns:
            PostOffice: The singleton PostOffice instance
        """
        return PostOffice.get_instance()
        
    def get_user_id(self) -> str:
        """
        Get the user ID associated with this LocalConfigManager instance.
        
        Returns:
            str: The user ID
        """
        return self.user_id