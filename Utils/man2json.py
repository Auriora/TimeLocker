import os
import re
import json
import traceback

# Precompile the regular expression pattern
section_pattern = re.compile(r'\.SH\s+"?([^"\n]+)"?\n((?:(?!\.SH\s+).|\n)*)')

def parse_man_sections(man_text: str, section_handlers: dict) -> dict:
    """
    Parse man page sections based on provided handler mapping.

    Args:
        man_text (str): The complete man page text
        section_handlers (dict): Mapping of section names to handler functions

    Returns:
        dict: Parsed sections with their corresponding results
    """

    # Find all sections
    sections = section_pattern.finditer(man_text)

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

    # Check if we have enough parts
    if len(parts) < 2:
        return {
            'executable': parts[0] if parts else None,
            'command': None,
            'parameters': []
        }

    return {
        'executable': parts[0],
        'command': parts[1],
        'parameters': parts[2:]
    }

def parse_command_line(text):
    clean_text = remove_formatting(text)
    match = match_command_pattern(clean_text)
    if not match:
        return None

    params = match.group(3).strip()
    param_list = split_parameters(params)

    return create_result_dict(match, param_list)

def remove_formatting(text):
    return re.sub(r'\\fB|\\fP', '', text)

def match_command_pattern(text):
    pattern = r'^(\w+)(?:\s+(\w+))?\s+(.+)$'
    return re.match(pattern, text)

def split_parameters(params):
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

    if current_param.strip():
        param_list.append(current_param.strip())

    return param_list

def create_result_dict(match, param_list):
    return {
        'executable': match.group(1),
        'command': match.group(2),
        'parameters': param_list
    }

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
    result = []
    for match in matches:
        status = match.group(1)
        desc = match.group(2)
        result.append({status: desc})
    return result

def parse_man_page_lines(text):
    # Split the text into individual option blocks
    blocks = text.strip().split('\n.PP\n')
    return [parse_option_block(block) for block in blocks if block.strip()]

def parse_option_block(block):
    lines = block.strip().split('\n')
    option_dict = {
        'short_flag': None,
        'long_flag': None,
        'value_type': None,
        'default': None,
        'description': None,
        'default_value': None
    }

    if lines:
        parse_flag_line(lines[0], option_dict)
        if len(lines) > 1:
            parse_description(lines[1:], option_dict)

    return option_dict

def parse_flag_line(flag_line, option_dict):
    option_dict['short_flag'] = parse_short_flag(flag_line)
    option_dict['long_flag'] = parse_long_flag(flag_line)
    parse_default_value(flag_line, option_dict)

def parse_short_flag(flag_line):
    short_flag_match = re.search(r'\\fB-(\w)\\fP', flag_line)
    return f"-{short_flag_match.group(1)}" if short_flag_match else None

def parse_long_flag(flag_line):
    long_flag_match = re.search(r'\\fB--([\w-]+)\\fP', flag_line)
    return f"--{long_flag_match.group(1)}" if long_flag_match else None

def parse_default_value(flag_line, option_dict):
    default_match = re.search(r'=(\[.*?\]|".*?"|auto|false)', flag_line)
    if default_match:
        default_value = default_match.group(1)
        if default_value == '[]':
            option_dict['value_type'] = 'list'
            option_dict['default'] = []
        elif default_value.startswith('"'):
            option_dict['value_type'] = 'string'
            option_dict['default'] = default_value.strip('"')
        else:
            option_dict['value_type'] = 'string'
            option_dict['default'] = default_value

def parse_description(description_lines, option_dict):
    description = ' '.join(description_lines).strip()
    description = re.sub(r'\\fB|\\fR|\\fP|\&\.', '', description)

    default_in_desc = re.search(r'\(default:\s*([^)]+)\)', description)
    if default_in_desc:
        option_dict['default_value'] = default_in_desc.group(1).strip()
        description = re.sub(r'\s*\(default:[^)]+\)', '', description)

    option_dict['description'] = description.strip()

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
    man_dir = "../sandbox/input/restic/man"
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
                    print(f"Error processing {file}:")
                    print(traceback.format_exc())

    # Write to JSON file
    with open('restic_commands.json', 'w', encoding='utf-8') as f:
        json.dump(all_commands, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    process_man_files()
