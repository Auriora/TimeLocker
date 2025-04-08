import os
import re
import json


def parse_man_sections(man_text, section_handlers):
    """
    Parse man page sections based on provided handler mapping.

    Args:
        man_text (str): The complete man page text
        section_handlers (dict): Mapping of section names to handler functions
    """

    # Regular expression to split on .SH sections
    # Captures the section name and content
    section_pattern = r'\.SH\s+"?([^"\n]+)"?\n((?:(?!\.SH\s+).|\n)*)'

    # Find all sections
    sections = re.finditer(section_pattern, man_text)

    results = {}

    for match in sections:
        section_name = match.group(1)
        section_content = match.group(2).strip()

        # If we have a handler for this section, process it
        if section_name in section_handlers:
            handler = section_handlers[section_name]
            results[section_name] = handler(section_content)

    return results


# Example handler functions
def parse_name_section(content):
    """Parse the NAME section."""
    parts = content.split(' - ', 1)
    return {
        'command': parts[0],
        'description': parts[1] if len(parts) > 1 else ''
    }

def parse_command_line_simple(text):
    # Remove man page formatting characters
    clean_text = re.sub(r'\\fB|\\fP', '', text)

    # Split into words
    parts = clean_text.split()

    return {
        'executable': parts[0],
        'command': parts[1],
        'parameters': parts[2:]
    }


def parse_command_line(text):
    # Remove man page formatting characters
    clean_text = re.sub(r'\\fB|\\fP', '', text)

    # Regular expression to match the components
    # Group 1: executable
    # Group 2: command (if exists)
    # Group 3: remaining parameters
    pattern = r'^(\w+)(?:\s+(\w+))?\s+(.+)$'

    match = re.match(pattern, clean_text)
    if not match:
        return None

    # Extract parameters, cleaning up and splitting
    params = match.group(3).strip()
    # Split parameters but preserve [...] groups
    param_list = []
    current_param = ''
    bracket_count = 0

    for char in params:
        if char == '[':
            bracket_count += 1
            current_param += char
        elif char == ']':
            bracket_count -= 1
            current_param += char
            if bracket_count == 0 and current_param.strip():
                param_list.append(current_param.strip())
                current_param = ''
        elif char.isspace() and bracket_count == 0:
            if current_param.strip():
                param_list.append(current_param.strip())
            current_param = ''
        else:
            current_param += char

    # Add the last parameter if exists
    if current_param.strip():
        param_list.append(current_param.strip())

    # Create result dictionary
    result = {
        'executable': match.group(1),
        'command': match.group(2),
        'parameters': param_list
    }

    return result

def parse_synopsis_section(content):
    """Parse the SYNOPSIS section."""
    # Remove formatting and extra whitespace
    clean_content = re.sub(r'\\fB|\\fP|\\fR', '', content)
    return clean_content.strip()


def parse_description_section(content):
    """Parse the DESCRIPTION section."""
    return content.strip()


def parse_exit_status(text):
    # Regular expression to match the status code and description
    pattern = r"Exit status is (\d+) if (.*?)\."

    # Find all matches in the text
    matches = re.finditer(pattern, text)

    # Create list of dictionaries with status code as key and description as value
    result = [
        {match.group(1): match.group(2).strip()}
        for match in matches
    ]

    return result

def parse_exit_status_section(content):
    """Parse the EXIT STATUS section."""
    status_pattern = r"Exit status is (\d+) if (.*?)\."
    matches = re.finditer(status_pattern, content)
    return [{status: desc} for status, desc in
            [(m.group(1), m.group(2)) for m in matches]]

def parse_man_page_lines(text):
    # Split the text into individual option blocks
    blocks = text.strip().split('\n.PP\n')

    options = []

    for block in blocks:
        lines = block.strip().split('\n')
        if not lines:
            continue

        # Initialize dictionary for this option
        option_dict = {
            'short_flag': None,
            'long_flag': None,
            'value_type': None,
            'default': None,
            'description': None,
            'default_value': None  # New field for defaults from description
        }

        # Parse the flag line
        flag_line = lines[0]

        # Extract short and long flags
        short_flag_match = re.search(r'\\fB-(\w)\\fP', flag_line)
        if short_flag_match:
            option_dict['short_flag'] = f"-{short_flag_match.group(1)}"

        long_flag_match = re.search(r'\\fB--([\w-]+)\\fP', flag_line)
        if long_flag_match:
            option_dict['long_flag'] = f"--{long_flag_match.group(1)}"

        # Extract default value from flag line
        default_match = re.search(r'=(\[.*?\]|".*?"|auto|false)', flag_line)
        if default_match:
            default_value = default_match.group(1)
            # Clean up the default value
            if default_value == '[]':
                option_dict['value_type'] = 'list'
                option_dict['default'] = []
            elif default_value.startswith('"'):
                option_dict['value_type'] = 'string'
                option_dict['default'] = default_value.strip('"')
            else:
                option_dict['value_type'] = 'string'
                option_dict['default'] = default_value

        # Parse description
        if len(lines) > 1:
            # Join all description lines and clean up formatting
            description = ' '.join(lines[1:]).strip()
            # Remove man page formatting
            description = re.sub(r'\\fB|\\fR|\\fP|\&\.', '', description)

            # Extract default value from description
            default_in_desc = re.search(r'\(default:\s*([^)]+)\)', description)
            if default_in_desc:
                option_dict['default_value'] = default_in_desc.group(1).strip()
                # Remove the default value from description (optional)
                description = re.sub(r'\s*\(default:[^)]+\)', '', description)

            option_dict['description'] = description.strip()

        options.append(option_dict)

    return options

def parse_options_section(content):
    """Parse the OPTIONS section."""
    # Split on .PP
    options = content.split('.PP')
    parsed_options = []

    for option in options:
        if not option.strip():
            continue

        lines = option.strip().split('\n')
        if not lines:
            continue

        flag_line = lines[0]
        description = ' '.join(lines[1:]).strip() if len(lines) > 1 else ''

        # Clean up formatting
        flag_line = re.sub(r'\\fB|\\fP|\\fR', '', flag_line)
        description = re.sub(r'\\fB|\\fP|\\fR|\&\.', '', description)

        parsed_options.append({
            'flags': flag_line,
            'description': description
        })

    return parsed_options

def parse_man_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    handlers = {
        'NAME': parse_name_section,
        'SYNOPSIS': parse_command_line,
        'DESCRIPTION': parse_description_section,
        'EXIT STATUS': parse_exit_status,
        'OPTIONS': parse_man_page_lines
    }

    result = parse_man_sections(content, handlers)
    return result

def process_man_files():
    man_dir = "../input/restic/man"
    all_commands = []

    # Walk through the man directory
    for root, dirs, files in os.walk(man_dir):
        for file in files:
            if file.endswith('.1'):  # Man pages typically end with .1
                file_path = os.path.join(root, file)
                try:
                    command_data = parse_man_file(file_path)
                    all_commands.append(command_data)
                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")

    # Write to JSON file
    with open('restic_commands.json', 'w', encoding='utf-8') as f:
        json.dump(all_commands, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    process_man_files()
