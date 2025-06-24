import os
import shutil
import subprocess
import atexit
import signal
from typing import List, Tuple, Optional, Dict

class ProcessManager:
    def __init__(self, global_file_manager):
        """
        Initialize the ProcessManager with a GlobalFileManager instance.
        
        Args:
            global_file_manager (GlobalFileManager): The GlobalFileManager instance to use for path management
        """
        self.global_file_manager = global_file_manager
        self._background_processes: Dict[int, subprocess.Popen] = {}
        # Register cleanup handler
        atexit.register(self._cleanup_background_processes)

    def _cleanup_background_processes(self):
        """
        Cleanup method to terminate all background processes when the main process exits.
        """
        for pid, process in self._background_processes.items():
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
                    except subprocess.TimeoutExpired:
                        process.kill()  # Force kill if it doesn't terminate
            except Exception:
                pass  # Ignore any errors during cleanup

    def run_script(self, file_path: str, args: List[str] = None, interpreter: str = None, cwd_path: Optional[str] = None) -> Tuple[str, str, int]:
        """
        Execute a script file and capture its output.
        
        Args:
            file_path (str): Path to the script file relative to files_directory
            args (List[str], optional): List of arguments to pass to the script
            interpreter (str, optional): Interpreter to use (e.g. "python", "node", "ruby")
            cwd_path (str, optional): Path to the working directory for the script execution. Defaults to the script's directory.
            
        Returns:
            Tuple[str, str, int]: (stdout, stderr, return_code)
            
        Raises:
            FileNotFoundError: If script file doesn't exist
            PermissionError: If script file isn't executable (when no interpreter specified)
            OSError: If there's an error during execution
            TimeoutError: If script takes too long or waits for stdin
        """
        # Get absolute path of the script
        script_path = self.global_file_manager.get_absolute_path(file_path)
        print("SCRIPT PATH: " + script_path)
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script file {file_path} not found")
            
        # Prepare the command
        if interpreter:
            # If interpreter path not fully specified, try to resolve it
            if not os.path.isabs(interpreter):
                resolved_interpreter = shutil.which(interpreter)
                # Use resolved path if found, otherwise fall back to original interpreter name
                if resolved_interpreter is not None:
                    interpreter = resolved_interpreter
            cmd = [interpreter, script_path]
        else:
            # Only make executable if running directly without interpreter
            if not os.access(script_path, os.X_OK):
                try:
                    os.chmod(script_path, 0o755)  # rwxr-xr-x
                except OSError:
                    raise PermissionError(f"Cannot make script {file_path} executable")
            cmd = [script_path]
            
        if args:
            cmd.extend(args)
            
        print("Running script:")
        print(cmd)
        try:
            # Run the script and capture output
            with open(os.devnull, 'r') as devnull:
                process = subprocess.Popen(
                    cmd,
                    stdin=devnull,  # Provide /dev/null as stdin
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd_path if cwd_path else os.path.dirname(script_path),
                    text=True  # Return strings instead of bytes
                )
                
                # Wait for completion with timeout
                try:
                    stdout, stderr = process.communicate(timeout=60)  # 60 second timeout
                    return stdout, stderr, process.returncode
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise TimeoutError("Script execution timed out or attempted to read from stdin")
            
        except OSError as e:
            raise OSError(f"Error executing script: {str(e)}")

    def run_command(self, command: str, args: List[str] = None, cwd_path: Optional[str] = None) -> Tuple[str, str, int]:
        """
        Execute an arbitrary command and capture its output.
        The command can be a name to be found in PATH (e.g., "ls") or a path to an executable (e.g., "./my_script.sh").

        Args:
            command (str): The command or path to the executable.
            args (List[str], optional): List of arguments to pass to the command.
            cwd_path (str, optional): Path to the working directory for the command execution. 
                                      If None, defaults to the current working directory of this process.
            
        Returns:
            Tuple[str, str, int]: (stdout, stderr, return_code)
            
        Raises:
            OSError: If there's an error during execution (e.g., command not found, permission denied).
            TimeoutError: If the command takes too long or attempts to read from stdin.
        """
        cmd_list = [command]
        if args:
            cmd_list.extend(args)
            
        print(f"Running command: {' '.join(cmd_list)}")
        if cwd_path:
            print(f"Working directory: {cwd_path}")
        else:
            print(f"Working directory: {os.getcwd()} (default)") 

        try:
            # Run the command and capture output
            with open(os.devnull, 'r') as devnull:
                process = subprocess.Popen(
                    cmd_list,
                    stdin=devnull,  # Provide /dev/null as stdin
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd_path, # If None, Popen uses parent's CWD
                    text=True     # Return strings instead of bytes
                )
                
                # Wait for completion with timeout
                try:
                    stdout, stderr = process.communicate(timeout=60)  # 60 second timeout
                    return stdout, stderr, process.returncode
                except subprocess.TimeoutExpired:
                    process.kill()
                    # Collect any output after kill. communicate() is safe to call multiple times.
                    stdout, stderr = process.communicate() 
                    raise TimeoutError(f"Command execution timed out or attempted to read from stdin: {' '.join(cmd_list)}")
            
        except OSError as e:
            # This will catch FileNotFoundError if 'command' is not found/executable,
            # or PermissionError, etc.
            raise OSError(f"Error executing command '{' '.join(cmd_list)}': {str(e)}")

    def run_script_background(self, file_path: str, args: List[str] = None, interpreter: str = None, cwd_path: Optional[str] = None) -> int:
        """
        Execute a script file in the background. The script will be terminated when the main process exits.
        
        Args:
            file_path (str): Path to the script file relative to files_directory
            args (List[str], optional): List of arguments to pass to the script
            interpreter (str, optional): Interpreter to use (e.g. "python", "node", "ruby")
            cwd_path (str, optional): Path to the working directory for the script execution. Defaults to the script's directory.
            
        Returns:
            int: Process ID (PID) of the background process
            
        Raises:
            FileNotFoundError: If script file doesn't exist
            PermissionError: If script file isn't executable (when no interpreter specified)
            OSError: If there's an error during execution
        """
        # Get absolute path of the script
        script_path = self.global_file_manager.get_absolute_path(file_path)
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script file {file_path} not found")
            
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(script_path), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Prepare the command
        if interpreter:
            if not os.path.isabs(interpreter):
                resolved_interpreter = shutil.which(interpreter)
                if resolved_interpreter is not None:
                    interpreter = resolved_interpreter
            cmd = [interpreter, script_path]
        else:
            if os.name != 'nt':  # Only check executable permission on non-Windows systems
                if not os.access(script_path, os.X_OK):
                    try:
                        os.chmod(script_path, 0o755)  # rwxr-xr-x
                    except OSError:
                        raise PermissionError(f"Cannot make script {file_path} executable")
            cmd = [script_path]
            
        if args:
            cmd.extend(args)

        # Prepare log file paths
        script_name = os.path.basename(file_path)
        stdout_log = os.path.join(logs_dir, f"{script_name}.out")
        stderr_log = os.path.join(logs_dir, f"{script_name}.err")
        
        try:
            # Run the script in background
            with open(stdout_log, 'a') as out, open(stderr_log, 'a') as err:
                # Set creation flags for Windows to create a new process group
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=out,
                    stderr=err,
                    cwd=cwd_path if cwd_path else os.path.dirname(script_path),
                    creationflags=creation_flags
                )
                
                # Store the process object for cleanup
                self._background_processes[process.pid] = process
                
                return process.pid
                
        except OSError as e:
            raise OSError(f"Error executing background script: {str(e)}") 