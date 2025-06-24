'''A collection of super-duper LLM-powered tools.'''
import sys
import os
from langchain_core.tools import tool
from leah.config.LocalConfigManager import LocalConfigManager
from leah.llm.LlmConnector import LlmConnector # Keep this for getLlmConnector

def getLlmConnector():
    config_manager = LocalConfigManager("default")
    return LlmConnector(config_manager, "gemini")


SUMMARIZE_TEXT_CONTEXT_TEMPLATE = """
Summarized Text:
{summary}
"""

EXTRACT_KEYWORDS_CONTEXT_TEMPLATE = """
Extracted Keywords:
{keywords}
"""

TRANSLATE_TEXT_CONTEXT_TEMPLATE = """
Translated Text ({target_language}):
{translated_text}
"""

@tool
def summarize_text(text_to_summarize: str) -> str:
    '''Summarizes the provided text using an LLM.

    Args:
        text_to_summarize: The text to be summarized.

    Returns:
        The summarized text, formatted within a template.
    '''
    try:
        llm = getLlmConnector()
        prompt = f"Please summarize the following text:\n\n{text_to_summarize}"
        summary = llm.query(prompt)
        return SUMMARIZE_TEXT_CONTEXT_TEMPLATE.format(summary=summary)
    except Exception as e:
        return f"Error during summarization: {str(e)}"

@tool
def extract_keywords(text_to_extract_from: str) -> str:
    '''Extracts keywords from the provided text using an LLM.

    Args:
        text_to_extract_from: The text from which to extract keywords.

    Returns:
        A string containing the extracted keywords, formatted within a template.
    '''
    try:
        llm = getLlmConnector()
        prompt = f"Please extract the main keywords from the following text. Return them as a comma-separated list:\n\n{text_to_extract_from}"
        keywords = llm.query(prompt)
        return EXTRACT_KEYWORDS_CONTEXT_TEMPLATE.format(keywords=keywords)
    except Exception as e:
        return f"Error during keyword extraction: {str(e)}"

@tool
def translate_text(text_to_translate: str, target_language: str) -> str:
    '''Translates the provided text to the target language using an LLM.

    Args:
        text_to_translate: The text to be translated.
        target_language: The language to translate the text into (e.g., "Spanish", "French", "German").

    Returns:
        The translated text, formatted within a template.
    '''
    try:
        llm = getLlmConnector()
        prompt = f"Please translate the following text into {target_language}:\n\n{text_to_translate}"
        translated_text = llm.query(prompt)
        return TRANSLATE_TEXT_CONTEXT_TEMPLATE.format(target_language=target_language, translated_text=translated_text)
    except Exception as e:
        return f"Error during translation: {str(e)}"

# Test the tools (optional, can be removed or commented out)
if __name__ == '__main__':
    sample_text = """
    The quick brown fox jumps over the lazy dog. This sentence is famous because it contains all of the letters of the English alphabet.
    It is often used for testing typewriters or keyboards. The early bird gets the worm, but the second mouse gets the cheese.
    Many proverbs offer wisdom in concise forms. Learning new things is always a good idea, as it broadens one's horizons.
    Artificial intelligence is a rapidly developing field with many potential applications, including natural language processing and machine learning.
    """
    print(f"Original Text:\n{sample_text}")
    
    summarized_output = summarize_text(sample_text)
    print(summarized_output)

    keywords_output = extract_keywords(sample_text)
    print(keywords_output)

    target_lang = "Spanish"
    translated_output = translate_text(sample_text, target_lang)
    print(translated_output)

    target_lang_2 = "Japanese"
    translated_output_2 = translate_text("Hello, how are you today?", target_lang_2)
    print(translated_output_2)
