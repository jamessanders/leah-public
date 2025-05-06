# Leah - AI Assistant Framework

A flexible framework for creating AI assistants with different personalities and personas, featuring web-based, command line and voice interfaces.

## Prerequisites

- Python 3.8 or higher

## Installation

Simply run the appropriate startup script for your operating system:

- **Windows**: Double-click `start.bat` or run it from the command line
- **Mac/Linux**: Run `./start.sh` from the terminal

The startup script will automatically:
- Install all required dependencies
- Set up the required environment
- Start the web serverr

### Alternative Manual Setup

If you prefer to set up components manually:

1. Install all dependencies:
```bash
pip install -r requirements.txt
pip install edge-tts pygame
```

2. Start the web server:
```bash
python src/leah_server.py
```

3. Access the web interface at `http://localhost:8001`

### Installing on iOS

You can install the Leah web app on your iPhone for a native app-like experience:

1. Open Safari on your iPhone
2. Navigate to your Leah instance (e.g., `http://localhost:8001` if running locally)
3. Tap the Share button (the square with an arrow pointing upward)
4. Scroll down and tap "Add to Home Screen"
5. Give the app a name or keep the default name
6. Tap "Add"

The app will now appear on your home screen with a dedicated icon. When launched from the home screen, it will run in full-screen mode without the Safari browser interface.

### Creating Users

To create a new user for the web interface, use the provided script:

```bash
python tools/create_user.py
```

This interactive script will:
- Prompt you for a username
- Ask you to set a password

### User Configuration

You can create a user-specific configuration file at `~/.leah/config.json`. This file will be merged with the default configuration, with your settings taking precedence.

Example `config.json`:
```json
{
  "keys": {
    "tavily": "your-tavily-api-key",
  },
  "connectors": {
    "gemini": {
      "api_key": "your-gemini-api-key"
    },
    "anthropic": {
      "api_key": "your-anthropic-api-key"
    },
    "openai": {
      "api_key": "your-open-api-key"
    }
  },
  "personas": {
    "default": {
      "voice": "en-US-JennyNeural"
    },
    "fred": {
      "description": "You are a custom AI assistant named fred.",
      "traits": [
        "You speak in riddles",
        "You enjoy tacos"
      ],
      "model": "gemma-3-4b-it",
      "temperature": 0.8,
      "voice": "en-US-GuyNeural"
    }
  }
}
```

The configuration file supports:
- API keys for various services (under `keys`)
- Connector configurations for different AI providers (under `connectors`)
- Custom persona configurations
- Voice settings
- Model parameters

API keys are required for certain features:
- Tavily API key for web search capabilities
- OpenAI API key for DALL-E image generation
- Gemini API key for Google's AI models
- Anthropic API key for Claude models

## Command-Line Interface

You can interact with Leah through a command-line interface using the `tools/leah-shell.py` script. The script supports both interactive and non-interactive modes.

### Interactive Mode

```bash
python tools/leah-shell.py --login --username your_username
```

Options:
- `--login`: Required for first-time authentication
- `--username`: Your username
- `--persona`: Specify which persona to use (default: Selene)

Once connected, you can:
- Type your messages and press Enter to send
- Use `/reset` to start a new conversation
- Type `exit` or `quit` to end the session

### Non-Interactive Mode

You can send single queries without entering interactive mode in several ways:

```bash
# Using positional arguments
python tools/leah-shell.py what is the weather like

# Using the --query flag
python tools/leah-shell.py --query "what is the weather like"

# Piping context into the query
echo "Current temperature is 72F" | python tools/leah-shell.py what is the weather like
```

In non-interactive mode:
- Only the response is printed (no system messages or prompts)
- The script exits after receiving the response
- You must authenticate first by running the script in interactive mode
- Error messages are sent to stderr

Note: When both positional arguments and --query flag are provided, the --query flag takes precedence.

## Voice Interface

The voice interface (`tools/voice_talk_interface.py`) allows you to interact with Leah using voice commands:

```bash
python tools/voice_talk_interface.py --device <number> --login --username your_username
```

Required options:
- `--device <number>`: Select your audio input device
- `--login`: Enable authentication
- `--username`: Your username

Additional options:
- `--list`: Show available audio devices

The voice interface listens for wake words like "computer", "hey computer", or "ok computer" before processing your command. After speaking a wake word, you'll hear a ping sound indicating the system is listening for your command.

Voice commands:
- Start commands with a wake word (e.g., "Hey computer, what's the weather?")
- Say "stop" to interrupt the current audio playback

Requirements:
- Python packages: sounddevice, numpy, whisper, pygame
- A working microphone
- Speakers for audio output

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.