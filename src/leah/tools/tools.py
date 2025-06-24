from leah.tools.math import add, subtract, multiply, divide
from leah.tools.linktools import fetch_stock_info, fetch_link_with_selenium
from leah.tools.tavily import web_search
from leah.tools.notes import put_note, get_note, list_notes, search_notes
from leah.tools.files import get_absolute_path_of_file, read_file, list_files, move_file, delete_file, download_file, read_file_partial, create_file, edit_file, insert_file_lines, delete_file_lines, read_file_lines, replace_file_lines, copy_file, append_file_lines, search_file_lines   
from leah.tools.process import run_command, run_script, run_python_script, run_bash_script, run_powershell_script, run_background_script
from leah.tools.task import getTools as getTaskTools
from leah.tools.messages import getTools as getMessageTools
from leah.tools.channels import getTools as getChannelTools
from leah.tools.custom_tools import get_current_datetime, get_system_information, generate_uuid, string_case_converter, json_validator, file_line_count, text_word_count, base64_encoder, base64_decoder, simple_math_calculator # Auto-generated: Added new tools from custom_tools.py
from leah.tools.super_duper_llm_tools import summarize_text, extract_keywords, translate_text # Added for LLM tools
from leah.tools.auto_doc_generator import generate_documentation # Added this line
from leah.tools.utils import get_current_directory, create_directory, path_exists, get_file_size, reverse_string # Added these new tools
from leah.tools.llm_utils import analyze_sentiment # Added these new LLM tools
from leah.tools.weather_tool import fetch_weather_info
from leah.tools.string_and_file_utils import get_file_extension, get_file_name, count_characters # Added new string and file utils


# Imports for custom_tools if they are not already present at the top level of custom_tools.py
# For example, if custom_tools.py uses 'import base64', we don't need to add it here
# as it's encapsulated. However, if tools.py itself needed these for some other direct reason,
# they would be here. Based on current structure, only the import from custom_tools is needed.

def getTools(persona: str, channel_id: str):
    return [
        add,
        subtract,
        multiply,
        divide,
        fetch_stock_info,
        fetch_link_with_selenium,
        web_search,
        put_note,
        get_note,
        list_notes,
        search_notes,
        get_absolute_path_of_file,
        edit_file,
        copy_file,
        append_file_lines,
        list_files,
        move_file,
        delete_file,
        download_file,
        read_file_partial,
        create_file,
        insert_file_lines,
        replace_file_lines,
        delete_file_lines,
        read_file_lines,
        search_file_lines,
        run_command,
        run_script,
        run_python_script,
        run_bash_script,
        run_powershell_script,
        run_background_script,
        # Auto-generated: Tools from custom_tools.py start
        get_current_datetime,
        get_system_information,
        generate_uuid,
        string_case_converter,
        json_validator,
        file_line_count,
        text_word_count,
        base64_encoder,
        base64_decoder,
        simple_math_calculator,
        # Auto-generated: Tools from custom_tools.py end
        summarize_text, # Added LLM tool
        extract_keywords, # Added LLM tool
        translate_text, # Added LLM tool
        generate_documentation, # Added this line
        get_current_directory, # Added new tool
        create_directory, # Added new tool
        path_exists, # Added new tool
        get_file_size, # Added new tool
        reverse_string, # Added new tool
        analyze_sentiment, # Added new LLM tool
        fetch_weather_info,
        get_file_extension, # Added new string and file util
        get_file_name, # Added new string and file util
        count_characters, # Added new string and file util
        *getTaskTools(persona, channel_id),
        *getMessageTools(persona, channel_id),
        *getChannelTools(persona, channel_id)
    ]
