from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify, g
from functools import wraps
from leah.actions import Actions, LogAction
from leah.config.AuthManager import AuthManager
from leah.llm.ChatApp import ChatApp
from leah.utils.ConversationStore import ConversationStore
from leah.config.GlobalConfig import GlobalConfig
from leah.config.LocalConfigManager import LocalConfigManager
from leah.utils.LogItem import LogItem, LogCollection
from leah.utils.LogManager import LogManager
from leah.utils.NotesManager import NotesManager
from leah.llm.StreamProcessor import StreamProcessor
from leah.utils.PostOffice import MailMan, PrintMessageHandler, PostOffice, Message, MessageHandler
from urllib.parse import urlparse
import asyncio
import edge_tts
import hashlib
import json
import mimetypes
import os
import queue
import random
import re
import threading
import tiktoken
import time
import traceback
import uuid

app = Flask(__name__)

# Create application context
app_context = app.app_context()
app_context.push()

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')

# Initialize mimetypes
mimetypes.init()

 # Initialize PostOffice singleton and system inbox
post_office = PostOffice.get_instance()    

class AgentMessageHandler(MessageHandler):
    def handle_message(self, message: Message) -> None:
        """Handle incoming messages by starting a ChatApp."""
        try:
            # Use the existing ChatApp from the message
            print(" +++ Processing message for inbox " + message.return_inbox_id)
            query, chatapp, source = message.body
            response = ""
            
            # Get all watch inboxes for this conversation
            post_office = PostOffice.get_instance()
            
            print(" +++ Query: " + query)
            for type, content in chatapp.stream(query, wait_timeout=1):
                if type == "content":
                    response += content
                elif type == "break":
                    response += "\n\n"
                elif type == "system":
                    print("Sending system message to inbox " + message.return_inbox_id)
                    # Send to original inbox
                    post_office.send_message(
                        to_inbox_id=message.return_inbox_id,
                        return_inbox_id=None,
                        body=(type, content, source)
                    )
            if chatapp.is_watching():
                print(" +++ Sending continue message to inbox " + message.return_inbox_id)
                post_office.send_message(
                    to_inbox_id="@continue",
                    return_inbox_id=message.return_inbox_id,
                    body=(chatapp, response)
                )
            else:
                print(" +++ No need to wait for continue message, sending final response to inbox " + message.return_inbox_id)
                # Send final response to original inbox
                post_office.send_message(
                    to_inbox_id=message.return_inbox_id,
                    return_inbox_id=None,
                    body=("content", response, "")
                )
                post_office.close_inbox(message.return_inbox_id)

        except Exception as e:
                    print(f"Error in ChatMessageHandler: {str(e)}")
                    print(traceback.format_exc())

class ContinueMessageHandler(MessageHandler):
    def handle_message(self, message: Message) -> None:
        chatapp, response = message.body
        return_inbox = message.return_inbox_id

        print(" +++ Continue message receiving...")

        if chatapp.is_watching():
            for (type,content,source) in chatapp.watch(5):
                if type == "content":
                    response += content
                elif type == "break":
                    response += "\n\n"
                elif type == "system":
                    post_office.send_message(
                        to_inbox_id=return_inbox,
                        return_inbox_id=None,
                        body=(type, content, source)
                    )
        if chatapp.is_watching():
            print(" +++ Still waiting sending continue message to inbox AGAIN " + return_inbox)
            post_office.send_message(
                to_inbox_id="@continue",
                return_inbox_id=return_inbox,
                body=(chatapp, response)
            )
        else:
            # Send final response to original inbox
            print(" +++ Done with continuation thread sending final response to inbox " + return_inbox)
            post_office.send_message(
                to_inbox_id=return_inbox,
                return_inbox_id=None,
                body=("content", response, "")
            )
            post_office.close_inbox(message.return_inbox_id)
                
        

# Initialize messaging system
def initialize_agents():
    print(" +++ Initializing agents")
    config = GlobalConfig()
    watched_inboxes = []
    for persona in config.get_personas():
        if config.get_persona_config(persona).get("threaded"):
            boxId = persona + "@agents"
            watched_inboxes.append(boxId)
            post_office.create_inbox(boxId)

    mail_man = MailMan(
        post_office=post_office,
        watched_inboxes=watched_inboxes,
        message_handler=AgentMessageHandler(),
        check_interval=0.5  # Check every 0.5 seconds
    )
    mail_man.start()  # Start the MailMan's internal operations

# Start messaging system initialization in a separate thread
messaging_thread = threading.Thread(target=initialize_agents, daemon=True)
messaging_thread.start()

def initialize_continue_messaging():
    print(" +++ Initializing continue messaging")
    post_office = PostOffice.get_instance()
    post_office.create_inbox("@continue")
    mail_man = MailMan(
        post_office=post_office,
        watched_inboxes=["@continue"],
        message_handler=ContinueMessageHandler(),
        check_interval=0.5  # Check every 0.5 seconds
    )
    mail_man.start()  # Start the MailMan's internal operations

# Start messaging system initialization in a separate thread
continue_messaging_thread = threading.Thread(target=initialize_continue_messaging, daemon=True)
continue_messaging_thread.start()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in the Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # If no token in header, check if it's in the request args
        if not token:
            token = request.args.get('token')
            
        if not token:
            return jsonify({"error": "Token is missing"}), 401
            
        # Get username from request args or headers
        username = request.args.get('username') or request.headers.get('X-Username')
        if not username:
            return jsonify({"error": "Username is required for token validation"}), 401
            
        # Validate the token
        auth_manager = AuthManager()
        if not auth_manager.verify_token(username, token):
            return jsonify({"error": "Invalid or expired token"}), 401
            
        # Set username on request state
        g.username = username
        g.token = token
        g.user_config = auth_manager.get_user_config(username, token)
        
        # Set LocalConfigManager on request state
        g.config_manager = LocalConfigManager(username)
            
        # Token is valid, proceed with the request
        return f(*args, **kwargs)
    
    return decorated

# Create a queue to hold the tuples
memory_builder_queue = queue.Queue()
indexing_queue = queue.Queue()

# Function to watch the queue and process items
def watch_memory_builder_queue():
    while True:
        try:
            # Wait for 2 minutes
            time.sleep(30)
            # Check if there is an item in the queue
            if not memory_builder_queue.empty():
                # Get the item from the queue
                username, persona, conversation_id = memory_builder_queue.get()
                # Process the item
                memory_builder(username, persona, conversation_id)
        except Exception as e:
            print(f"Error in watch_queue: {e}")
            tb = traceback.format_exc()
            print(tb)

# Start the background thread
threading.Thread(target=watch_memory_builder_queue, daemon=True).start()

def watch_indexing_queue():
    while True:
        time.sleep(5)
        try:
            username, persona, query, full_response = indexing_queue.get()
            run_indexer(username, persona, query, full_response)
        except Exception as e:
            print(f"Error in watch_indexing_queue: {e}")
            print(traceback.format_exc())

threading.Thread(target=watch_indexing_queue, daemon=True).start()

def memory_builder(username, persona, convo_id):
    print("Running memory builder")
    config_manager = LocalConfigManager(username, persona)
    notesManager = config_manager.get_notes_manager()
    memories = notesManager.get_note(f"memories/memories.txt")
    if not memories:
        notesManager.put_note(f"memories/memories.txt", "No previous notes.")
    memories = notesManager.get_note(f"memories/memories.txt")
   
    prompt = memory_template(memories)
    
    orig_chatapp = ChatApp(config_manager, persona, convo_id)
    history = orig_chatapp.history

    chatapp = ChatApp(config_manager, persona)
    chatapp.history = history
    chatapp.set_system_content(f"You are {persona}. You are a rigorous and detailed note taker.\n\n" + prompt)
    result = ChatApp.unstream(chatapp.stream("Generate new notes based on the conversation and the previous notes.", use_tools=False))
    notesManager.put_note(f"memories/memories.txt", result)
 
def run_indexer(username, persona, query, full_response): 
    print("Running indexer")
    config_manager = LocalConfigManager(username, persona)
    convo = (query + "\n" + full_response).split(" ")
    if len(convo) > 300:
        convo = convo[:299]
    convo = " ".join(convo)
    script = f"""
Return five index terms relevant to the conversation below. Return the only the terms as a comma seperated list.

The conversation:

{convo}
""" 
    chatapp = ChatApp(config_manager,"summer")
    result = ChatApp.unstream(chatapp.stream(script, use_tools=False))
    terms = result.split(",")
    print("Logging terms: " + terms)
    logger = config_manager.get_log_manager()
    for term in terms:
        term = term.strip()
        logger.log_index_item(term, "[USER] " + query)
        logger.log_index_item(term, "[ASSISTANT] " + full_response)


voice_files = {}
voice_queue = queue.Queue()

def voice_generator():
    while True:
        try:
            time.sleep(1)
            while not voice_queue.empty():
                voice_filename, plain_text_content, voice = voice_queue.get()
                voice_dir = os.path.join(WEB_DIR, 'voice')
                voice_file_path = os.path.join(voice_dir, voice_filename)
                if not os.path.exists(voice_file_path):
                   print(f"Generating voice for {voice_filename} as {voice_file_path}")
                   async def generate_voice():
                     communicate = edge_tts.Communicate(text=plain_text_content, voice=voice)
                     await communicate.save(voice_file_path)
                   asyncio.run(generate_voice())
                   del voice_files[voice_filename]         
        except Exception as e:
            print(f"Error in voice_generator: {e}")
threading.Thread(target=voice_generator, daemon=True).start()

@app.route('/')
def serve_index():
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_file(filename):
    # Get the MIME type based on the file extension
    mime_type, _ = mimetypes.guess_type(filename)
    # Special case for JavaScript files
    if filename.endswith('.js'):
        mime_type = 'text/javascript'
    # If no MIME type is found, default to 'application/octet-stream'
    elif mime_type is None:
        mime_type = 'application/octet-stream'
    # Serve the file with the correct MIME type
    return send_from_directory(WEB_DIR, filename, mimetype=mime_type)

@app.route('/generated_images/<username>/<persona>/<path:filename>')
def serve_image(username, persona, filename):
    config_manager = LocalConfigManager(username, persona)
    image_dir = os.path.join(config_manager.get_persona_path("images"))
    return send_from_directory(image_dir, filename)

# Function to strip markdown
def strip_markdown(text):
    """Remove markdown formatting from text."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]*`', '', text)
    # Remove bold and italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    return text.strip()

def filter_emojis(text: str) -> str:
    """Remove emojis from text."""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', text)

def filter_urls(text: str) -> str:
    """Replace URLs with a placeholder text."""
    url_pattern = r'https?://\S+'
    return re.sub(url_pattern, 'URL', text)

def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    if not text:
        return 0
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))

def check_for_urls(message: str) -> tuple[bool, str]:
    """
    Check if a message contains any URLs and return the first URL found.
    
    Args:
        message (str): The message to check for URLs
        
    Returns:
        tuple[bool, str]: A tuple containing (has_url, extracted_url)
            - has_url (bool): True if a URL was found, False otherwise
            - extracted_url (str): The first URL found, or None if no URL was found
    """
    url_pattern = r'https?://\S+'
    url_matches = re.findall(url_pattern, message)
    has_url = len(url_matches) > 0
    extracted_url = url_matches[0] if has_url else None
    return has_url, extracted_url

def context_template(message: str, context: str, extracted_url: str) -> str:
    now = datetime.now()
    today = now.strftime("%B %d, %Y")
    return f"""
Here is some context for the query:
{context}

Source: {extracted_url} (Last updated {today})

Here is the query:
{message}

Answer the query based on the context.
"""


def generate_voice_file(plain_text_content, username, persona):
    config = GlobalConfig()
    voice = config.get_voice(persona)
    voice_dir = os.path.join(WEB_DIR, 'voice')
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S"+str(random.randint(0, 1000000)))
    voice_file_path = os.path.join(voice_dir, f'{voice}_{username}_{timestamp}.mp3')
    plain_text_content = strip_markdown(plain_text_content)
    plain_text_content = filter_emojis(plain_text_content)
    plain_text_content = filter_urls(plain_text_content)
    # Remove '#' character
    plain_text_content = plain_text_content.replace('#', '')
    filename = os.path.basename(voice_file_path)
    voice_files[filename] = (plain_text_content, voice)
    voice_queue.put((filename, plain_text_content, voice))
    return filename

def system_message(message: str) -> str:
    json_message = json.dumps({'type': 'system', 'content': message})
    return f"data: {json_message}\n\n"

def memory_template(memories: str) -> str:
    return f"""
Previous notes:

START OF PREVIOUS NOTES
{memories}
END OF PREVIOUS NOTES

Instructions:
Create detailed notes about the conversation and combine them with the previous memories.
Make sure to keep a profile of the user and their interests.
Make sure to keep a profile of your own knowledge, particularily any information about the user.
Make sure to keep a profile of your self and you relationship with the user.
These notes are written from your own perspective and about the user.
Remove duplicate information.
Include a list of instructions for yourself to follow to better taylor your responses going forward.
Use a format that is easy for you to use for reference later.
The reply should be no longer than 1000 words.
Don't include any other text than the notes.
Don't use NotesAction.put_note
"""
    
def search_past_logs(config_manager, persona, query, previous_reply=None):
    if previous_reply:
        previous_reply = f"Previous Reply: {previous_reply}"
    else:
        previous_reply = ""
    script = f"""
Return five index terms that can be used to search past conversations relevant to the following query, return the terms as a simple commas seperated list, return only the terms and nothing else

{previous_reply}


The query is: {query}

""" 
    terms = ask_agent("summer", script)
    print("Terms: " + terms)
    logManager = config_manager.get_log_manager()
    logs = []
    for term in terms.split(","):
        for log in logManager.search_log_item(persona, term.strip()):
            if len(log) > 256:
                log = log[:255]
            logs.append(log)
    print("Found " + str(len(logs)) + " logs")
    log_items = LogCollection.fromLogLines(logs)
    return log_items.generate_report()

def print_convo(convo):
    print("CONVO_START")
    for c in convo:
        message = c["content"][0:255]
        print(f"{c['role']}: {message}")
    print("CONVO_END\n\n")


@app.route('/query', methods=['POST'])
@token_required
def query():
    max_tokens = 17000
    data = request.get_json()
    username = g.username
    user_config = g.user_config
    config_manager = LocalConfigManager(g.username, persona = data.get('persona', 'default'))
    original_query = data.get('query', '')
    
    def generate_stream():    
        # Get the persona from the request, default to 'leah' if not specified
        persona = data.get('persona', 'leah')
        # Assuming config is available in this context
        config = GlobalConfig()
        personas = config.get_persona_choices(user_config.get("groups", ["default"]))
        if persona not in personas:
            yield system_message("Persona not found")
            yield f"data: {json.dumps({'type': 'end', 'content': 'END OF RESPONSE'})}\n\n"
            return
        use_broker = config.get_use_broker(persona)
        
        # Get conversation history from conversation store
        conversation_id = data.get('conversation_id')
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation_id})}\n\n"


        notesManager = config_manager.get_notes_manager()
        memories = notesManager.get_note(f"memories/memories.txt")
        
        if memories:
            memories = "These are your memories from previous conversations: \n\n" + memories
        else:
            memories = ""

        full_response = ""
        chatapp = ChatApp(config_manager, persona, conversation_id)
        voice_buffer = ""
 
        original_query = data.get('query', '')
        if data.get('context',''):
            data['query'] = context_template(data.get('query', ''), data.get('context', ''), 'User provided context')
            
       
        if memories:
            chatapp.set_system_content(chatapp.system_content + "\n\n" + memories)
        
        send_buffer = ""
        last_send_time = time.time()
        for type, content in chatapp.stream(data.get("query",""), wait_timeout=30):
            if type == "break":
                if send_buffer:
                    yield f"data: {json.dumps({'content': send_buffer})}\n\n"
                    send_buffer = ""
                    last_send_time = time.time()
                yield f"data: {json.dumps({'type': 'break', 'content': ''})}\n\n"
                continue
            elif type == "system":
                print("System message: " + str(content))
                yield f"data: {json.dumps({'type': 'system', 'content': str(content)})}\n\n"
                continue
            elif type == "content":
                if content:
                    voice_buffer += content
                    full_response += content
                    if voice_buffer.endswith(('.', '!', '?')) and len(voice_buffer) > 256:
                        # Generate voice for the complete sentence
                        voice_filename = generate_voice_file(voice_buffer, username, persona)
                        voice_file_info = {"filename": voice_filename}
                        yield f"data: {json.dumps(voice_file_info)}\n\n"
                        # Reset the buffer
                        voice_buffer = ""
                    if time.time() - last_send_time > 0.2 and len(send_buffer) > 128:
                        send_buffer += content
                        yield f"data: {json.dumps({'content': send_buffer})}\n\n"
                        last_send_time = time.time()
                        send_buffer = ""
                    else:
                        send_buffer += content

        if send_buffer:
            yield f"data: {json.dumps({'content': send_buffer})}\n\n"

        if voice_buffer:
            voice_filename = generate_voice_file(voice_buffer, username, persona)
            voice_file_info = {"filename": voice_filename}
            yield f"data: {json.dumps(voice_file_info)}\n\n"
        

        yield f"data: {json.dumps({'type': 'end', 'content': 'END OF RESPONSE'})}\n\n"
        log_manager = config_manager.get_log_manager()
        log_manager.log_chat("user", original_query)
        log_manager.log_chat("assistant", full_response)
        # Add the current request to the cleanup queue after the response is sent
        update_post_request_queue(username, persona, conversation_id)
        # indexing_queue.put((username, persona, original_query, full_response))



    # Method to add to the queue
    def update_post_request_queue(username, persona, conversation_id):
        # Clear all existing items from the cleanup queue
        # Remove existing items for this persona from the cleanup queue
        items = []
        while not memory_builder_queue.empty():
            try:
                item = memory_builder_queue.get_nowait()
                if item[0] != persona:  # Keep items for other personas
                    items.append(item)
            except queue.Empty:
                break
        # Put back items we want to keep
        for item in items:
            memory_builder_queue.put(item)

        memory_builder_queue.put((username, persona, conversation_id))
    return app.response_class(generate_stream(), mimetype='text/event-stream')

@app.route('/voice/<voice_filename>')
def serve_voice(voice_filename):
    voice_dir = os.path.join(WEB_DIR, 'voice')
    voice_file_path = os.path.join(voice_dir, voice_filename)
    if not os.path.exists(voice_file_path):
        plain_text_content, voice = voice_files[voice_filename]
        print(f"Just in time Generating voice for {voice_filename} as {voice_file_path}")
        async def generate_voice():
            communicate = edge_tts.Communicate(text=plain_text_content, voice=voice)
            await communicate.save(voice_file_path)
        asyncio.run(generate_voice())
        del voice_files[voice_filename]
    return send_from_directory(voice_dir, voice_filename)

@app.route('/personas', methods=['GET'])
@token_required
def get_personas():
    config = GlobalConfig()
    user_config = g.user_config
    if user_config:
        groups = user_config.get("groups", ["default"])
    else:
        groups = ["default"]
    personas = config.get_persona_choices(groups)
    return jsonify(personas)

@app.route('/avatars/<requested_avatar>')
def serve_avatar(requested_avatar):
    img_dir = os.path.join(WEB_DIR, 'img')
    default_avatar = 'avatar.png'
    # Check if the requested avatar exists
    if os.path.exists(os.path.join(img_dir, requested_avatar)):
        return send_from_directory(img_dir, requested_avatar)
    else:
        return send_from_directory(img_dir, default_avatar)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    auth_manager = AuthManager()
    token = auth_manager.authenticate(username, password)
    
    if token:
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/protected', methods=['GET'])
@token_required
def protected_route():
    return jsonify({"message": "This is a protected route. You have valid authentication."}), 200

@app.route('/watch', methods=['GET'])
@token_required
def watch_conversation():
    conversation_id = request.args.get('conversation_id')
    persona = request.args.get('persona')
    if not conversation_id:
        return jsonify({"error": "Conversation ID is required"}), 400
    if not persona:
        return jsonify({"error": "Persona is required"}), 400

    config_manager = LocalConfigManager(g.username, persona)
    chatapp = ChatApp(config_manager, persona, conversation_id)
    watch_status = chatapp.get_watch_status()
    return jsonify(watch_status)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001) 