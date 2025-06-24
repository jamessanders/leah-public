'''A collection of utility LLM-powered tools.'''
import sys
import os
from langchain_core.tools import tool
from leah.config.LocalConfigManager import LocalConfigManager
from leah.llm.LlmConnector import LlmConnector # Keep this for getLlmConnector

def getLlmConnector():
    config_manager = LocalConfigManager("default")
    return LlmConnector(config_manager, "gemini")


@tool
def generate_creative_text(prompt: str) -> str:
    '''Generates creative text formats, like poems, code, scripts, musical pieces, email, letters, etc.

    Args:
        prompt: The prompt to generate creative text from.

    Returns:
        The generated creative text.
    '''
    try:
        llm = getLlmConnector()
        # No specific template for creative text, as it can be highly varied.
        # The prompt itself should guide the LLM towards the desired output format.
        creative_text = llm.query(prompt)
        return creative_text
    except Exception as e:
        return f"Error during creative text generation: {str(e)}"


@tool
def answer_question(question: str, context: str = None) -> str:
    '''Answers a question, optionally using provided context.

    Args:
        question: The question to be answered.
        context: Optional context to help answer the question.

    Returns:
        The answer to the question.
    '''
    try:
        llm = getLlmConnector()
        if context:
            prompt = f"Based on the following context, please answer the question.\n\nContext:\n{context}\n\nQuestion: {question}"
        else:
            prompt = f"Please answer the following question: {question}"
        answer = llm.query(prompt)
        return answer
    except Exception as e:
        return f"Error during question answering: {str(e)}"


@tool
def analyze_sentiment(text: str) -> str:
    '''Analyzes the sentiment of a piece of text (e.g., positive, negative, neutral).

    Args:
        text: The text to analyze.

    Returns:
        The sentiment of the text.
    '''
    try:
        llm = getLlmConnector()
        prompt = f"Please analyze the sentiment of the following text and return one of: Positive, Negative, or Neutral.\n\nText: {text}"
        sentiment = llm.query(prompt)
        # Basic validation to ensure the LLM returns one of the expected sentiments.
        # More robust validation could be added if needed.
        if sentiment.strip().capitalize() not in ["Positive", "Negative", "Neutral"]:
            # Fallback or attempt to re-query if the response is not as expected.
            # For now, we'll just return the raw response if it doesn't match.
            pass # Or handle more gracefully
        return sentiment
    except Exception as e:
        return f"Error during sentiment analysis: {str(e)}"
