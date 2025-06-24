import random
import datetime
from langchain_core.tools import tool

@tool
def is_palindrome(text: str) -> bool:
    """Checks if a string is a palindrome.
    A palindrome is a word, phrase, number, or other sequence of characters
    that reads the same backward as forward, such as 'madam' or 'racecar'.
    Ignores spaces, punctuation, and capitalization.
    """
    processed_text = ''.join(filter(str.isalnum, text)).lower()
    return processed_text == processed_text[::-1]

@tool
def generate_random_number(min_val: int, max_val: int) -> int:
    """Generates a random integer between min_val and max_val (inclusive)."""
    if min_val > max_val:
        return "Error: min_val cannot be greater than max_val."
    return random.randint(min_val, max_val)

@tool
def get_day_of_week(date_string: str) -> str:
    """Takes a date string in YYYY-MM-DD format and returns the day of the week.
    Example: get_day_of_week('2024-12-25') returns 'Wednesday'.
    """
    try:
        date_obj = datetime.datetime.strptime(date_string, '%Y-%m-%d')
        return date_obj.strftime('%A')
    except ValueError:
        return "Error: Invalid date format. Please use YYYY-MM-DD."
