'''
This module contains custom tools developed for Leah.
'''
import datetime
import platform
import uuid
import json
import base64
import ast
import re # For safe math evaluation

from langchain_core.tools import tool

@tool
def get_current_datetime():
    """Returns the current date and time."""
    return datetime.datetime.now().isoformat()

@tool
def get_system_information():
    """Returns basic system information (OS, version)."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version()
    }

@tool
def generate_uuid():
    """Generates a universally unique identifier (UUID v4)."""
    return str(uuid.uuid4())

@tool
def string_case_converter(text: str, case_type: str):
    """
    Converts a string to various cases.
    Args:
        text: The input string.
        case_type: The target case type. 
                   Options: "uppercase", "lowercase", "titlecase", "sentencecase".
    """
    if case_type == "uppercase":
        return text.upper()
    elif case_type == "lowercase":
        return text.lower()
    elif case_type == "titlecase":
        return text.title()
    elif case_type == "sentencecase":
        return text.capitalize()
    else:
        return "Invalid case_type. Options: uppercase, lowercase, titlecase, sentencecase."

@tool
def json_validator(json_string: str):
    """
    Validates if a given string is a valid JSON.
    Args:
        json_string: The string to validate.
    Returns:
        A dictionary with "is_valid" (bool) and a "message" (str).
    """
    try:
        json.loads(json_string)
        return {"is_valid": True, "message": "Valid JSON"}
    except json.JSONDecodeError as e:
        return {"is_valid": False, "message": str(e)}

@tool
def file_line_count(file_path: str) -> int:
    """
    Reads a file and returns the total number of lines in it.
    Args:
        file_path: The path to the file.
    Returns:
        The total number of lines in the file, or an error message string.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return len(lines)
    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def text_word_count(text: str) -> int:
    """
    Takes a string of text and returns the total number of words.
    Args:
        text: The input string.
    Returns:
        The total number of words in the text.
    """
    words = text.split()
    return len(words)

@tool
def base64_encoder(data: str, encoding: str = 'utf-8') -> str:
    """
    Encodes a given string into Base64 format.
    Args:
        data: The string to encode.
        encoding: The encoding of the input string (default: 'utf-8').
    Returns:
        The Base64 encoded string.
    """
    encoded_bytes = base64.b64encode(data.encode(encoding))
    return encoded_bytes.decode(encoding)

@tool
def base64_decoder(encoded_data: str, encoding: str = 'utf-8') -> str:
    """
    Decodes a Base64 encoded string back to its original form.
    Args:
        encoded_data: The Base64 encoded string.
        encoding: The encoding for the output string (default: 'utf-8').
    Returns:
        The decoded string, or an error message if decoding fails.
    """
    try:
        decoded_bytes = base64.b64decode(encoded_data.encode(encoding))
        return decoded_bytes.decode(encoding)
    except Exception as e:
        return f"Error decoding Base64 string: {str(e)}"

# Allowed operations for safe math calculator
_ALLOWED_OPERATORS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
    ast.USub: lambda a: -a,
}

# Allowed node types for safe math calculator
_ALLOWED_NODE_TYPES = (
    ast.Expression, ast.Num, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub
)

def _safe_eval_math_expr(node):
    """Helper function to safely evaluate a math expression node."""
    if not isinstance(node, tuple(_ALLOWED_NODE_TYPES)):
        # Check if it's a number (Python 3.7 compatibility for ast.Num)
        if isinstance(node, (int, float)):
            return node
        # For ast.Constant in Python 3.8+
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        raise TypeError(f"Unsupported node type: {type(node).__name__}")

    if isinstance(node, ast.Num): # For older Python versions
        return node.n
    elif isinstance(node, ast.Constant): # For Python 3.8+
        if isinstance(node.value, (int, float)):
            return node.value
        else:
            raise ValueError("Only numeric constants are allowed.")
    elif isinstance(node, ast.BinOp):
        left = _safe_eval_math_expr(node.left)
        right = _safe_eval_math_expr(node.right)
        operator_func = _ALLOWED_OPERATORS.get(type(node.op))
        if operator_func:
            return operator_func(left, right)
        else:
            raise TypeError(f"Unsupported operator: {type(node.op).__name__}")
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval_math_expr(node.operand)
        operator_func = _ALLOWED_OPERATORS.get(type(node.op))
        if operator_func:
            return operator_func(operand)
        else:
            raise TypeError(f"Unsupported unary operator: {type(node.op).__name__}")
    elif isinstance(node, ast.Expression):
        return _safe_eval_math_expr(node.body)
    else:
        # This case should ideally be caught by the initial isinstance check
        raise TypeError(f"Unexpected node type during evaluation: {type(node).__name__}")

@tool
def simple_math_calculator(expression: str) -> str:
    """
    Evaluates a simple mathematical string expression safely.
    Supports: +, -, *, /, ** (power), and parentheses.
    Args:
        expression: The mathematical expression string (e.g., "10 + 5 * (2 - 1)").
    Returns:
        The result of the calculation as a float, or an error message string.
    """
    try:
        # Validate expression against potentially harmful characters/patterns
        # This is a basic check; more robust validation might be needed for production
        if not re.match(r"^[0-9\.\+\-\*\/\(\)\s\^\*\*]+$", expression):
            return "Error: Expression contains invalid characters."
        
        # Replace ^ with ** for ast parser compatibility
        expression = expression.replace('^', '**')

        # Parse the expression into an AST (Abstract Syntax Tree)
        node = ast.parse(expression, mode='eval')

        # Validate all nodes in the AST
        for sub_node in ast.walk(node):
            if not isinstance(sub_node, tuple(_ALLOWED_NODE_TYPES)):
                 # Allow ast.Constant if its value is a number (for Python 3.8+)
                if isinstance(sub_node, ast.Constant) and isinstance(sub_node.value, (int, float)):
                    continue
                return f"Error: Disallowed operation or character: {type(sub_node).__name__}"

        # Evaluate the AST
        result = _safe_eval_math_expr(node.body) # node.body for 'eval' mode
        return result
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError) as e:
        return f"Error evaluating expression: {str(e)}"
    except Exception as e:
        # Catch any other unexpected errors during parsing or evaluation
        return f"An unexpected error occurred: {str(e)}"

