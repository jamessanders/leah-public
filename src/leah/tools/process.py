from typing import Any, Dict, List
import os
import subprocess
import venv
from langchain_core.tools import tool
from leah.utils.FilesSandbox import FilesSandbox
from leah.utils.GlobalFileManager import GlobalFileManager
from leah.utils.ProcessManager import ProcessManager
from leah.config.LocalConfigManager import LocalConfigManager

runningProcesses = []

def get_process_manager():
    config_manager = LocalConfigManager("default")
    file_manager = GlobalFileManager(config_manager, '/', config_manager.get_sandbox_directory_path())
    return ProcessManager(file_manager)

def get_file_manager():
    config_manager = LocalConfigManager("default")
    return GlobalFileManager(config_manager, '/', config_manager.get_sandbox_directory_path())

def get_sandbox_path():
    return LocalConfigManager("default").get_sandbox_directory_path()

@tool
def run_command(command: str, command_args: List[str], cwd: str):
    """
    Execute an arbitrary command and capture its output.
    """
    if not command:
        return "Command is required"

    if not cwd:
        cwd = get_sandbox_path()
        
    process_manager = get_process_manager()
    try:
        stdout, stderr, return_code = process_manager.run_command(command, command_args, cwd_path=cwd)
        result = f"Command execution completed with return code {return_code}\n\n"
        
        if stdout:
            result += "Standard Output:\n" + stdout + "\n"
        if stderr:
            result += "Standard Error:\n" + stderr + "\n"

        result += "\n\nthe user has not seen the output of this script." 
        print(result)
            
        return result
        
    except FileNotFoundError:
        print("FileNotFoundError")
        return f"Command {command} not found"
    except PermissionError as e:
        print("PermissionError")
        return str(e)
    except TimeoutError:
        print("TimeoutError")
        return "Script execution was terminated because it timed out or attempted to read from stdin"
    except Exception as e:
        print(e)
        return f"Error executing script: {str(e)}"

def _run_script(file_path: str, command_args: List[str], interpreter: str = None, cwd: str = None):
    """
    Execute a script file and capture its output. Can specify an interpreter (e.g. python, node) or run directly. 
    Scripts that attempt to read from stdin will be terminated.
    """
    if not file_path:
        return "File path is required"
    
    # Parse arguments if provided
    args_list = command_args if command_args else None
    if not cwd:
        cwd = get_sandbox_path()
       
    process_manager = get_process_manager()
    try:
        stdout, stderr, return_code = process_manager.run_script(file_path, command_args, interpreter, cwd_path=cwd)
        result = f"Script execution completed with return code {return_code}\n\n"
        
        if stdout:
            result += "Standard Output:\n" + stdout + "\n"
        if stderr:
            result += "Standard Error:\n" + stderr + "\n"

        result += "\n\nthe user has not seen the output of this script." 
        print(result)
            
        return result
        
    except FileNotFoundError:
        print("FileNotFoundError")
        return f"Script file {file_path} not found"
    except PermissionError as e:
        print("PermissionError")
        return str(e)
    except TimeoutError:
        print("TimeoutError")
        return "Script execution was terminated because it timed out or attempted to read from stdin"
    except Exception as e:
        print(e)
        return f"Error executing script: {str(e)}"

@tool
def run_script(file_path: str, command_args: List[str], interpreter: str = None, cwd: str = None):
    """
    Execute a script file and capture its output. Can specify an interpreter (e.g. python, node) or run directly. 
    Scripts that attempt to read from stdin will be terminated.
    """
    return _run_script(file_path, command_args, interpreter, cwd)

@tool
def run_python_script(file_path: str, command_args: List[str], cwd: str):
    """
    Execute a Python script using python3 interpreter and capture its output.
    """
    return _run_script(file_path, command_args, interpreter="python3", cwd=cwd)

@tool
def run_bash_script(file_path: str, command_args: List[str], cwd: str):
    """
    Execute a Bash script and capture its output.
    """
    return _run_script(file_path, command_args, interpreter="bash", cwd=cwd)

@tool
def run_powershell_script(file_path: str, command_args: List[str], cwd: str):
    """
    Execute a PowerShell script and capture its output.
    """
    return _run_script(file_path, command_args, interpreter="powershell", cwd=cwd)



@tool
def run_background_script(file_path: str, command_args: List[str], interpreter: str = None, cwd: str = None):
    """
    Execute a script in the background. The script will continue running even after the command completes.
    """
    if not file_path:
        return "File path is required"
    if not cwd:
        cwd = get_sandbox_path()
    # Parse arguments if provided
    args_list = command_args if command_args else None
    
    process_manager = get_process_manager()
    try:
        pid = process_manager.run_script_background(file_path, args_list, interpreter, cwd_path=cwd) 
        return f"Script started in background with PID: {pid}"
    except Exception as e:
        return f"Error starting script: {str(e)}"


