from typing import Any, Dict
import os
import subprocess
import venv
from leah.actions.IActions import IAction
from leah.utils.FilesSandbox import FilesSandbox
from leah.utils.ProcessManager import ProcessManager
from leah.llm.ChatApp import ChatApp
runningProcesses = []

class ProcessAction(IAction):
    def __init__(self, config_manager, persona, query, chat_app: ChatApp):
        self.config_manager = config_manager
        self.persona = persona
        self.query = query
        self.chat_app = chat_app
        self.file_manager = FilesSandbox(config_manager.get_file_manager(), "sandbox")
    def getTools(self):
        return [
            (self.run_script,
             "run_script",
             "Execute a script file and capture its output. Can specify an interpreter (e.g. python, node) or run directly. Scripts that attempt to read from stdin will be terminated.",
             {"file_path": "<the full path of the script to run including subdirectories>", "args": "<optional space-separated list of arguments>", "interpreter": "<optional interpreter to use (e.g. python, node)>"}),
            (lambda args: self.run_script({**args, "interpreter": "python3"}),
             "run_python_script",
             "Execute a Python script using python3 interpreter and capture its output.",
             {"file_path": "<the full path of the Python script to run>", "args": "<optional space-separated list of arguments>"}),
            (lambda args: self.run_script({**args, "interpreter": "bash"}),
             "run_bash_script",
             "Execute a Bash script and capture its output.",
             {"file_path": "<the full path of the Bash script to run>", "args": "<optional space-separated list of arguments>"}),
            (lambda args: self.run_script({**args, "interpreter": "powershell"}),
             "run_powershell_script",
             "Execute a PowerShell script and capture its output.",
             {"file_path": "<the full path of the PowerShell script to run>", "args": "<optional space-separated list of arguments>"}),
            (self.run_venv_script,
             "run_venv_script",
             "Execute a Python script in a virtual environment. Creates or uses an existing venv, installs requirements if provided, and runs the script.",
             {"file_path": "<the full path of the Python script to run>", 
              "venv_path": "<path to create/use virtual environment>",
              "requirements": "<optional comma-separated list of pip packages to install>",
              "args": "<optional space-separated list of arguments>"}),
            (self.run_background_script,
             "run_background_script",
             "Execute a script in the background. The script will continue running even after the command completes.",
             {"file_path": "<the full path of the script to run>",
              "args": "<optional space-separated list of arguments>",
              "interpreter": "<optional interpreter to use (e.g. python, node)>"}),
        ]

    def run_script(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        if not file_path:
            yield ("result", "File path is required")
            return
        
        # Parse arguments if provided
        args_str = arguments.get("args", "")
        args = args_str.split() if args_str else None
        
        # Get interpreter if provided
        interpreter = arguments.get("interpreter", None)
        
        yield ("system", f"Running script: {file_path}" + 
               (f" with interpreter: {interpreter}" if interpreter else "") +
               (f" with args: {args_str}" if args_str else ""))

       
        process_manager = ProcessManager(self.file_manager)
        
        try:
            stdout, stderr, return_code = process_manager.run_script(file_path, args, interpreter)
            result = f"Script execution completed with return code {return_code}\n\n"
            
            if stdout:
                result += "Standard Output:\n" + stdout + "\n"
            if stderr:
                result += "Standard Error:\n" + stderr + "\n"

            result += "\n\nthe user has not seen the output of this script." 
            print(result)
                
            yield ("result", result)
            
        except FileNotFoundError:
            print("FileNotFoundError")
            yield ("result", f"Script file {file_path} not found")
        except PermissionError as e:
            print("PermissionError")
            yield ("result", str(e))
        except TimeoutError:
            print("TimeoutError")
            yield ("result", "Script execution was terminated because it timed out or attempted to read from stdin")
        except Exception as e:
            print(e)
            yield ("result", f"Error executing script: {str(e)}")

    def run_venv_script(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        venv_path = arguments.get("venv_path", "")
        requirements = arguments.get("requirements", "")
        args_str = arguments.get("args", "")
        
        if not file_path or not venv_path:
            yield ("end", "File path and virtual environment path are required")
            return
        
        yield ("system", f"Setting up virtual environment at {venv_path} and running script: {file_path}")
        file_manager = self.file_manager
        
        try:
            # Create virtual environment if it doesn't exist
            if not os.path.exists(venv_path):
                yield ("system", "Creating new virtual environment...")
                venv.create(venv_path, with_pip=True)
            
            # Get path to Python and pip in virtual environment
            if os.name == 'nt':  # Windows
                python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
                pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
            else:  # Unix-like
                python_path = os.path.join(venv_path, 'bin', 'python')
                pip_path = os.path.join(venv_path, 'bin', 'pip')
            
            # Install requirements if provided
            if requirements:
                yield ("system", "Installing required packages...")
                packages = [pkg.strip() for pkg in requirements.split(',')]
                for package in packages:
                    try:
                        process = subprocess.Popen(
                            [pip_path, 'install', package],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        stdout, stderr = process.communicate()
                        if process.returncode != 0:
                            yield ("system", f"Warning: Failed to install {package}: {stderr}")
                    except Exception as e:
                        yield ("system", f"Warning: Error installing {package}: {str(e)}")
            
            # Get absolute path of script file
            abs_file_path = os.path.abspath(file_path)
            if not os.path.exists(abs_file_path):
                yield ("result", f"Script file {abs_file_path} not found")
                return
            file_path = abs_file_path
            # Prepare command to run the script
            cmd = [python_path, file_path]
            if args_str:
                cmd.extend(args_str.split())
            
            # Run the script
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.abspath(file_path))
            )
            
            stdout, stderr = process.communicate(timeout=60)
            result = f"Script execution completed with return code {process.returncode}\n\n"
            
            if stdout:
                result += "Standard Output:\n" + stdout + "\n"
            if stderr:
                result += "Standard Error:\n" + stderr + "\n"
            
            yield ("result", result)
            
        except FileNotFoundError:
            yield ("result", f"Script file {file_path} not found")
        except PermissionError as e:
            yield ("result", str(e))
        except subprocess.TimeoutExpired:
            process.kill()
            yield ("result", "Script execution was terminated because it timed out")
        except Exception as e:
            yield ("result", f"Error executing script: {str(e)}")

    def run_background_script(self, arguments: Dict[str, Any]):
        file_path = arguments.get("file_path", "")
        if not file_path:
            yield ("result", "File path is required")
            return
        
        # Parse arguments if provided
        args_str = arguments.get("args", "")
        args = args_str.split() if args_str else None
        
        # Get interpreter if provided
        interpreter = arguments.get("interpreter", None)
        
        yield ("system", f"Running script in background: {file_path}" + 
               (f" with interpreter: {interpreter}" if interpreter else "") +
               (f" with args: {args_str}" if args_str else ""))
        
        process_manager = ProcessManager(self.file_manager)

        try:
            pid = process_manager.run_script_background(file_path, args, interpreter) 
            yield ("result", f"Script started in background with PID: {pid}")
        except Exception as e:
            yield ("result", f"Error starting script: {str(e)}") 


