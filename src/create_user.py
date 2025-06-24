#!/usr/bin/env python
import sys
import os

from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify, g
from functools import wraps
from leah.actions import Actions, LogAction
from leah.actors.TaskActor import TaskActor
from leah.config.AuthManager import AuthManager
from leah.llm.ChatApp import ChatApp
from leah.utils.Message import MessageType
from leah.utils.SubscriptionService import SubscriptionService
from leah.utils.PubSub import PubSub
from leah.utils.ConversationStore import ConversationStore
from leah.config.GlobalConfig import GlobalConfig
from leah.config.LocalConfigManager import LocalConfigManager
from leah.utils.LogItem import LogItem, LogCollection
from leah.utils.LogManager import LogManager
from leah.utils.NotesManager import NotesManager
from leah.llm.StreamProcessor import StreamProcessor
from leah.actors.PersonaActor import PersonaActor
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
from leah.utils.PubSub import Message


# Add the src directory to the Python path
import leah.config.LocalConfigManager as LCM
import leah.config.AuthManager as AM

def main():

    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    auth_manager = AM.AuthManager(LCM.LocalConfigManager("auth"))
    
    if auth_manager.create_user(username, password):
        print(f"User '{username}' created successfully.")
    else:
        print(f"Failed to create user '{username}'. Username may already exist.")

if __name__ == "__main__":
    main() 