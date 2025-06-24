'''
Automated Documentation Generator

This script will analyze Python code and generate Markdown documentation.
'''

import ast
import argparse
from langchain_core.tools import tool # Added this line

def parse_python_file(file_path):
    '''Parses a Python file and extracts information about its structure.'''
    with open(file_path, "r") as source:
        tree = ast.parse(source.read(), filename=file_path)

    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            docstring = ast.get_docstring(node)
            functions.append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "docstring": docstring if docstring else "No docstring found."
            })
        elif isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node)
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_docstring = ast.get_docstring(item)
                    methods.append({
                        "name": item.name,
                        "args": [arg.arg for arg in item.args.args],
                        "docstring": method_docstring if method_docstring else "No docstring found."
                    })
            classes.append({
                "name": node.name,
                "docstring": docstring if docstring else "No docstring found.",
                "methods": methods
            })

    return functions, classes

def generate_markdown(functions, classes):
    '''Generates Markdown documentation from parsed code information.'''
    markdown = "# Code Documentation\\n\\n"

    if functions:
        markdown += "## Functions\\n\\n"
        for func in functions:
            markdown += f"### ` {func['name']}({ ', '.join(func['args']) })`\\n"
            markdown += f"{func['docstring']}\\n\\n"
    
    if classes:
        markdown += "## Classes\\n\\n"
        for cls in classes:
            markdown += f"### `class {cls['name']}`\\n"
            markdown += f"{cls['docstring']}\\n\\n"
            if cls['methods']:
                markdown += "#### Methods\\n\\n"
                for method in cls['methods']:
                    markdown += f"##### ` {method['name']}({ ', '.join(method['args']) })`\\n"
                    markdown += f"{method['docstring']}\\n\\n"

    if not functions and not classes:
        markdown += "No functions or classes found to document.\\n"

    return markdown

@tool # Added this decorator
def generate_documentation(file_path: str):
    '''Generates Markdown documentation for a Python file and saves it.

    Args:
        file_path: The path to the Python file to document.

    Returns:
        The path to the generated Markdown file or an error message.
    '''
    try:
        functions, classes = parse_python_file(file_path)
        markdown_docs = generate_markdown(functions, classes)
        
        output_filename = file_path.replace(".py", "_docs.md")
        with open(output_filename, "w") as f:
            f.write(markdown_docs)
        return f"Documentation generated: {output_filename}"

    except FileNotFoundError:
        return f"Error: File not found at {file_path}"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Markdown documentation for a Python file.")
    parser.add_argument("file_path", help="The path to the Python file to document.")
    args = parser.parse_args()

    print(f"Attempting to generate documentation for: {args.file_path}")
    result = generate_documentation(args.file_path)
    print(result)