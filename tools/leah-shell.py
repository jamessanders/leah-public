#!/usr/bin/env python3

import warnings
warnings.filterwarnings('ignore', message='.*OpenSSL.*')

import argparse
import getpass
import json
import os
import requests
import sys
from pathlib import Path

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Command Line Interface for Leah')
parser.add_argument('args', nargs='*', help='Query string (if provided without --query flag)')
parser.add_argument('--login', action='store_true', help='Login to the server')
parser.add_argument('--username', type=str, help='Username for login')
parser.add_argument('--persona', type=str, default='Selene', help='Persona to use (default: Selene)')
parser.add_argument('--query', type=str, help='Initial query to send (optional)')
args = parser.parse_args()

# Set up host and token storage
host = os.environ.get('LEAH_HOST', "http://localhost:8001")
token_dir = os.path.expanduser("~/.leah")
token_file = os.path.join(token_dir, ".cmdln_token")

def load_token():
    """Load the stored token, username and conversation_id if they exist."""
    try:
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                data = json.load(f)
                return data.get('token'), data.get('username'), data.get('conversation_id')
    except Exception as e:
        print(f"Error loading token: {e}")
    return None, None, None

def save_token(token, username, conversation_id=None):
    """Save the token, username and conversation_id to the token file."""
    try:
        os.makedirs(token_dir, exist_ok=True)
        with open(token_file, 'w') as f:
            json.dump({
                'token': token, 
                'username': username,
                'conversation_id': conversation_id
            }, f)
    except Exception as e:
        print(f"Error saving token: {e}")

def login(username, password):
    """Login to the Leah service and get a token."""
    try:
        response = requests.post(f'{host}/login', json={'username': username, 'password': password})
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            if token:
                save_token(token, username)
                return token
        print("Login failed.")
    except Exception as e:
        print(f"Error during login: {e}")
    return None

def send_query(query, token, username, context=None):
    """Send a query to the Leah service."""
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Username': username
    }
    
    # Load the current conversation_id
    _, _, conversation_id = load_token()
    
    # Prepare the request payload
    payload = {
        'query': query,
        'persona': args.persona,
    }
    
    # Add context to payload if provided
    if context:
        payload['context'] = context
    
    # Add conversation_id to payload if it exists
    if conversation_id:
        payload['conversation_id'] = conversation_id
    
    try:
        with requests.post(f'{host}/query', 
                         json=payload,
                         headers=headers,
                         stream=True) as response:
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', 'Unknown error occurred')
                    print(f"\nError: {error_message} (Status code: {response.status_code})", file=sys.stderr)
                except json.JSONDecodeError:
                    print(f"\nError: {response.text} (Status code: {response.status_code})", file=sys.stderr)
                return
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        try:
                            data_json = json.loads(decoded_line[6:])
                            if data_json.get('type') == 'conversation_id':
                                # Store the conversation_id when received
                                conversation_id = data_json.get('id')
                                save_token(token, username, conversation_id)
                                continue
                            elif data_json.get('type') == 'end':
                                continue
                            elif data_json.get('type') == 'system':
                                if not args.query:  # Only show system messages in interactive mode
                                    # print("System: " + data_json.get('content'), end="\n", flush=True)
                                    continue
                            elif data_json.get('content'):
                                print(data_json.get('content'), end="", flush=True)
                        except json.JSONDecodeError:
                            if not args.query:  # Only show error in interactive mode
                                print("Failed to decode JSON from response.")
            if not args.query:  # Only print newline in interactive mode
                print()
            
    except Exception as e:
        print(f"Error sending query: {e}", file=sys.stderr)

def reset_conversation(token, username):
    """Reset the conversation by clearing the stored conversation_id."""
    save_token(token, username, None)
    print("Conversation reset. Starting a new conversation.")

def main():
    # Get query from either positional args or --query flag
    query = None
    
    # First check for --query flag
    if args.query is not None:
        query = args.query
    # Then check for positional arguments
    elif args.args:
        query = ' '.join(args.args)
    
    # If query is provided (either way), require existing login
    if query:
        token, stored_username, _ = load_token()
        if not token or not stored_username:
            print("Error: Please run the script without a query first to log in.", file=sys.stderr)
            sys.exit(1)
        
        # Check if there's data being piped in
        context = None
        if not sys.stdin.isatty():
            context = sys.stdin.read()
        
        send_query(query, token, stored_username, context)
        return

    # Interactive mode
    context = None
    if not sys.stdin.isatty():
        context = sys.stdin.read()
        print(f"Collected {len(context)} characters as context from stdin")
        # Reset stdin to terminal
        sys.stdin = open('/dev/tty')
    
    token, stored_username, conversation_id = load_token()
    username = args.username or stored_username
    
    if args.login or not token or not username:
        if not username:
            username = input("Username: ")
        password = getpass.getpass(prompt='Password: ')
        token = login(username, password)
        if not token:
            return
    
    print("Connected to Leah. Type 'exit' or 'quit' to end the session.")
    print("Use '/reset' to start a new conversation.")
    
    while True:
        try:
            query = input("\n> ")
            print(" ")
            if query.lower() in ['exit', 'quit']:
                break
            if query.strip() == '/reset':
                reset_conversation(token, username)
                continue
            if query.strip():
                send_query(query, token, username, context)
                # Clear context after first use
                if context:
                    print("Cleared initial context for subsequent queries")
                    context = None
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main() 