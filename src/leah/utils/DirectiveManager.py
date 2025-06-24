from datetime import datetime
import os
from pathlib import Path
import platform
from jinja2 import Environment, BaseLoader, TemplateNotFound

class DirectiveIncludeExtension:
    """Custom Jinja2 extension to handle directive inclusion"""
    
    def __init__(self, directive_manager):
        self.directive_manager = directive_manager

    def __call__(self, name):
        """Handle directive inclusion by name"""
        content = self.directive_manager.get_directive_by_name(name)
        if content is None:
            raise TemplateNotFound(f"Directive '{name}' not found")
        return content

class DirectiveManager:
    def __init__(self, local_config_manager):
        self.local_config_manager = local_config_manager
        self.env = Environment(loader=BaseLoader())
        self.directive_include = DirectiveIncludeExtension(self)
        
        # Add custom filter for directive inclusion
        self.env.filters['directive'] = self.directive_include

    def _get_template_vars(self):
        """Get the default template variables"""
        return {
            'HOME': os.path.expanduser('~'),
            'SANDBOX_DIR': self.local_config_manager.get_sandbox_directory_path(),
            'CURRENT_TIME': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'CWD': os.getcwd(),
            'OPERATING_SYSTEM': platform.system()
        }

    def _process_template(self, content: str) -> str:
        """Process a template string with Jinja2"""
        try:
            template = self.env.from_string(content)
            return template.render(**self._get_template_vars())
        except Exception as e:
            print(f"Error processing template: {e}")
            return content

    def load_directives(self):
        all_directives = []
        potential_paths = [
            os.path.join(self.local_config_manager.get_persona_config_directory(), 'directives'),
            os.path.join(self.local_config_manager.get_home_config_directory(), 'directives'),
            os.path.join(self.local_config_manager.get_config().get_home_config_directory(), "directives"),
            os.path.join(self.local_config_manager.get_config().get_project_directory(), 'directives'),
        ]
        print("Loading directives from: " + str(potential_paths))
        found_any = False
        for path in potential_paths:
            if os.path.exists(path):
                all_directives.extend(self._load_from_path(path))
                found_any = True
        
        if not found_any:
            raise FileNotFoundError("No directives found in any configured path.")
            
        return all_directives

    def _load_from_path(self, path: Path):
        directives_in_path = []
        if path.is_dir():
            for item_name in os.listdir(path):
                item_path = os.path.join(path, item_name)
                if os.path.isfile(item_path):
                    try:
                        with open(item_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Process the template before adding it
                            processed_content = self._process_template(content)
                            directives_in_path.append(processed_content)
                    except Exception as e:
                        print(f"Error reading directive file {item_path}: {e}")
        return directives_in_path

    def get_directive_by_name(self, directive_name: str) -> str:
        """
        Finds and loads a specific directive file by its name.
        The .md extension is automatically appended to the directive_name.

        Args:
            directive_name (str): The name of the directive file (without .md extension).

        Returns:
            Optional[str]: The content of the directive file if found, otherwise None.
        """
        potential_paths = [
            os.path.join(self.local_config_manager.get_persona_config_directory(), 'directives'),
            os.path.join(self.local_config_manager.get_home_config_directory(), 'directives'),
            os.path.join(self.local_config_manager.get_config().get_home_config_directory(), "directives"),
            os.path.join(self.local_config_manager.get_config().get_project_directory(), 'directives'),
        ]

        filename = f"{directive_name}.md"

        for dir_path in potential_paths:
            directive_file_path = os.path.join(dir_path, filename)
            if os.path.exists(directive_file_path) and os.path.isfile(directive_file_path):
                try:
                    with open(directive_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Process the template before returning
                        return self._process_template(content)
                except Exception as e:
                    print(f"Error reading directive file {directive_file_path}: {e}")
                    # If one path fails, we might still find it in another, so continue
        
        return None
