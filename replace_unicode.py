#!/usr/bin/env python3
import os
import re
import sys

def replace_unicode_chars(content):
    # Replace Unicode dashes with ASCII dashes
    content = content.replace('‑', '-')
    
    # Replace Unicode ellipsis with ASCII ellipsis
    content = content.replace('…', '...')
    
    # Replace Unicode bullet points with ASCII asterisks
    content = content.replace('•', '*')
    
    # Replace Unicode greater than or equal to with ASCII >=
    content = content.replace('≥', '>=')
    
    # Replace Unicode less than or equal to with ASCII <=
    content = content.replace('≤', '<=')
    
    return content

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file contains any Unicode characters that need to be replaced
        original_content = content
        content = replace_unicode_chars(content)
        
        # Only write to the file if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_directory(directory):
    changes_made = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Only process Markdown files
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                if process_file(file_path):
                    changes_made += 1
    return changes_made

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isfile(target):
            if process_file(target):
                print("1 file updated.")
            else:
                print("No files updated.")
        elif os.path.isdir(target):
            changes = process_directory(target)
            print(f"{changes} files updated.")
        else:
            print(f"Error: {target} is not a valid file or directory.")
    else:
        # Default to processing the docs directory
        docs_dir = os.path.join(os.getcwd(), 'docs')
        if os.path.isdir(docs_dir):
            changes = process_directory(docs_dir)
            print(f"{changes} files updated.")
        else:
            print(f"Error: {docs_dir} directory not found.")