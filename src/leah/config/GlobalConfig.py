#!/usr/bin/env python3

"""
Config - A module for managing configuration settings for the Leah script.
"""

import os
import json
from typing import Dict, Any
from copy import deepcopy
from datetime import datetime

class GlobalConfig:
    """Configuration management class for the Leah script."""
    
    def __init__(self):
        """Initialize the configuration by loading from config.json."""
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../config.json')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json and merge with .hey.config.json if it exists."""
        # Load the main config file
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Check for user config in home directory
        home_dir = os.path.expanduser("~")
        user_config_path = os.path.join(home_dir, '.leah/config.json')
        
        if os.path.exists(user_config_path):
            try:
                with open(user_config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Merge user config with main config
                config = self._merge_configs(config, user_config)
            except Exception as e:
                print(e)
        
        return config
    
    def _merge_configs(self, main_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with main config, with user config taking precedence."""
        # Create a deep copy of the main config to avoid modifying it
        merged_config = deepcopy(main_config)
        
        # Merge top-level keys
        for key, value in user_config.items():
            if key not in merged_config:
                merged_config[key] = value
            elif isinstance(value, dict) and isinstance(merged_config[key], dict):
                # Recursively merge dictionaries
                merged_config[key] = self._merge_configs(merged_config[key], value)
            else:
                # User config takes precedence
                merged_config[key] = value
        
        return merged_config
    
    def _get_persona_config(self, persona='default') -> Dict[str, Any]:
        """Get the configuration for a persona, merging with default if needed."""
        if persona == 'default':
            return self.config['personas']['default']
        
        # Start with a deep copy of the default persona
        persona_config = deepcopy(self.config['personas']['default'])
        
        # Merge in the selected persona's settings
        if persona in self.config['personas']:
            for key, value in self.config['personas'][persona].items():
                persona_config[key] = value
        
        return persona_config
    
    def get_stable_diffusion_config(self) -> str:
        """Get the Stable Diffusion URL from config."""
        return self.config.get('stable_diffusion', {})

    def get_system_content(self, persona='default') -> str:
        """Get the system content based on the specified persona."""
        persona_config = self._get_persona_config(persona)
        return f"{persona_config['description']}\n" + "\n".join(f"- {trait}" for trait in persona_config['traits']) + "\n- the users current time and date is " + datetime.now().strftime("%I:%M %p (%Z) on %A, %B %d %Y")
    
    def get_use_broker(self, persona='default') -> bool:
        """Get the use broker setting for the specified persona."""
        return self._get_persona_config(persona).get('use_broker', False)

    def get_model(self, persona='default') -> str:
        """Get the model for the specified persona."""
        return self._get_persona_config(persona)['model']
    
    def get_temperature(self, persona='default') -> float:
        """Get the temperature setting for the specified persona."""
        return self._get_persona_config(persona)['temperature']
    
    def get_prompt_script(self, persona='default') -> str:
        """Get the prompt script for the specified persona."""
        return self._get_persona_config(persona).get('prompt_script', None)  
    
    def get_voice(self, persona='default') -> str:
        """Get the voice for the specified persona."""
        return self._get_persona_config(persona)['voice']
    
    def get_ollama_url(self, persona='default') -> str:
        """Get the LMStudio API URL from config."""
        if self._get_persona_config(persona).get('connector'):
            connector = self.config['connectors'][self._get_persona_config(persona).get('connector')]
            return connector.get('url', None)
        else:
            return None
    
    def get_connector_type(self, persona='default') -> str:
        """Get the connector type for the specified persona."""
        if self._get_persona_config(persona).get('connector'):
            connector = self.config['connectors'][self._get_persona_config(persona).get('connector')]
            return connector['type']
        return 'local'

    def get_ollama_api_key(self, persona='default') -> str:
        """Get the LMStudio API key from config."""
        if self._get_persona_config(persona).get('connector'):
            connector = self.config['connectors'][self._get_persona_config(persona).get('connector')]
            return connector.get('api_key', None)
        else:
            return None 

    def get_keys(self) -> Dict[str, str]:
        """Get the keys from config."""
        return self.config['keys']

    def get_headers(self) -> Dict[str, str]:
        """Get the headers from config."""
        return self.config['headers']
    
    def get_persona_choices(self, groups: list[str]) -> list:
        """Get the list of available personas."""
        visible_personas = []
        for persona, config in self.config['personas'].items():
            if config.get('visible', False) and any(group in groups for group in config.get('group', "").split(",")):
                visible_personas.append(persona)
        return visible_personas
    
    def get_after_response(self, persona='default') -> str:
        """Get the after response for the specified persona."""
        return self._get_persona_config(persona).get('after_response', None)
    
    def get_tools(self, persona='default') -> list[str]:
        """Get the list of available tools."""
        return self._get_persona_config(persona).get('tools', [])
    
    def get_agent_descriptions(self) -> dict[str, str]:
        """Get the list of available agent descriptions."""
        agent_descriptions = {}
        for persona, config in self.config['personas'].items():
            if config.get('agent_description', None):
                agent_descriptions[persona] = config['agent_description']
        return agent_descriptions
    
    def get_personas(self) -> dict[str, Any]:
        """Get the configuration for all personas."""
        return self.config['personas']
    
    def get_persona_config(self, persona='default') -> dict[str, Any]:
        """Get the configuration for a persona."""
        return self._get_persona_config(persona)
    
    