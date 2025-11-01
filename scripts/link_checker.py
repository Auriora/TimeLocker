import os
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# Configuration
ROOT = Path(os.getcwd())  # This will be the project root
DOCS_DIR = ROOT / 'docs'
EXCLUDE_DIRS = {'.venv', 'venv', 'env', '.git', '.pytest_cache', '__pycache__', 'node_modules'}
EXCLUDE_AMBIGUOUS_FILENAMES = {'README.md', '_template.md'}

# Global debug flag
DEBUG_MODE = False


def parse_args():
    parser = argparse.ArgumentParser(description="Check and fix broken markdown links.")
    parser.add_argument("--fix", action="store_true", help="Automatically fix broken links.")
    parser.add_argument("--debug", action="store_true", help="Enable debug output.")
    parser.add_argument(
            "--fail-on-style",
            action="store_true",
            help="Treat canonical link style issues as errors (non-zero exit).",
    )
    args = parser.parse_args()
    global DEBUG_MODE
    if args.debug:
        DEBUG_MODE = True
    return args


def list_files_recursive(directory: Path, exclude_dirs: set[str]) -> list[Path]:
    """Recursively list all files under a directory, excluding specified directory names."""
    if DEBUG_MODE:
        print(f"DEBUG: list_files_recursive called with directory={directory.relative_to(ROOT) if directory.is_relative_to(ROOT) else directory}")
        print(f"DEBUG:   Current directory.name: '{directory.name}', exclude_dirs: {exclude_dirs}")

    # Check if the current directory itself is in the exclude list
    if directory.name in exclude_dirs:
        if DEBUG_MODE:
            print(f"DEBUG:   Skipping excluded directory: {directory.relative_to(ROOT) if directory.is_relative_to(ROOT) else directory}")
        return []

    files = []
    try:
        for entry in directory.iterdir():
            if entry.is_dir():
                # Recursive call will handle its own exclusion check
                files.extend(list_files_recursive(entry, exclude_dirs))
            elif entry.is_file() and entry.suffix == '.md':  # Only add markdown files here
                files.append(entry)
    except PermissionError as e:
        if DEBUG_MODE:
            print(f"DEBUG: PermissionError accessing {directory}: {e}")
    except FileNotFoundError as e:
        if DEBUG_MODE:
            print(f"DEBUG: FileNotFoundError accessing {directory}: {e}")
    return files


def extract_links(markdown_content: str) -> list[dict]:
    """
    Extract markdown links of the form [text](target) ignoring images ![]().
    """
    links = []
    link_re = re.compile(r'(?<!\!)\[([^\]]*)\]\(([^)\s]+)(?:(?:\s+"[^"]*")?)\)')

    for idx, line in enumerate(markdown_content.splitlines()):
        for match in link_re.finditer(line):
            links.append({
                    'full_markdown_link': match.group(0),
                    'link_text':          match.group(1),
                    'target_url':         match.group(2),
                    'line_number':        idx + 1,
                    'line_content':       line,
                    'start_col':          match.start(0),
                    'end_col':            match.end(0)
            })
    return links


def is_external_link(target: str) -> bool:
    return target.startswith(('http://', 'https://'))


def is_anchor(target: str) -> bool:
    return target.startswith('#')


def resolve_target(
        from_file: Path,
        target: str,
        filename_to_paths_map: dict[str, list[Path]],
        stem_to_paths_map: dict[str, list[Path]]
) -> Path | None:
    """Normalize a relative link target from a file to an absolute path following a clear priority."""
    if DEBUG_MODE:
        print(f"DEBUG: resolve_target called for from_file={from_file.relative_to(ROOT) if from_file.is_relative_to(ROOT) else from_file}, target='{target}'")
    file_part = target.split('#')[0]
    if not file_part:
        if DEBUG_MODE:
            print(f"DEBUG:   Anchor-only link, returning None")
        return None  # Anchor-only link

    # Priority 1: Explicit paths (relative or absolute from root)
    if file_part.startswith('/'):
        resolved_path = (ROOT / file_part.lstrip('/')).resolve()
        if DEBUG_MODE:
            print(
                    f"DEBUG:   Attempting to resolve as absolute path: {resolved_path.relative_to(ROOT) if resolved_path.is_relative_to(ROOT) else resolved_path}")
        return resolved_path if resolved_path.is_relative_to(ROOT) else None
    if file_part.startswith('./') or file_part.startswith('../'):
        resolved_path = (from_file.parent / file_part).resolve()
        if DEBUG_MODE:
            print(
                    f"DEBUG:   Attempting to resolve as explicit relative path: {resolved_path.relative_to(ROOT) if resolved_path.is_relative_to(ROOT) else resolved_path}")
        return resolved_path if resolved_path.is_relative_to(ROOT) else None

    # Priority 2: Bare filename. Check for a file/directory in the same directory first.
    path_in_same_dir = (from_file.parent / file_part).resolve()
    if path_in_same_dir.exists() and path_in_same_dir.is_relative_to(ROOT):
        if DEBUG_MODE:
            print(f"DEBUG:   Resolved as bare filename/directory in same dir: {path_in_same_dir.relative_to(ROOT)}")
        return path_in_same_dir

    # Priority 3: Bare filename. Try to resolve by stem (filename without extension).
    file_stem = Path(file_part).stem
    if file_stem in stem_to_paths_map:
        matches = [p for p in stem_to_paths_map[file_stem] if p.is_relative_to(ROOT)]
        if len(matches) == 1:
            if DEBUG_MODE:
                print(f"DEBUG:   Resolved as bare filename by unique stem: {matches[0].relative_to(ROOT)}")
            return matches[0]
        elif DEBUG_MODE:
            print(f"DEBUG:   Found {len(matches)} matches for stem '{file_stem}', not unique.")

    # Priority 4: Bare filename. Try to resolve by exact filename (including extension).
    if file_part in filename_to_paths_map:
        matches = [p for p in filename_to_paths_map[file_part] if p.is_relative_to(ROOT)]
        if len(matches) == 1:
            if DEBUG_MODE:
                print(f"DEBUG:   Resolved as bare filename by unique filename: {matches[0].relative_to(ROOT)}")
            return matches[0]
        elif DEBUG_MODE:
            print(f"DEBUG:   Found {len(matches)} matches for filename '{file_part}', not unique.")

    if DEBUG_MODE:
        print(f"DEBUG:   Could not resolve target '{target}', returning None")
    return None


def get_relative_path(from_file: Path, to_file: Path, original_target_url: str) -> str:
    """
    Calculates the relative path from from_file to to_file, preserving the original anchor.
    """
    anchor = ""
    if '#' in original_target_url:
        anchor = '#' + original_target_url.split('#', 1)[1]

    try:
        relative_path = os.path.relpath(to_file, from_file.parent)
    except ValueError:
        return str(to_file) + anchor  # Fallback to absolute path if relative is not possible

    # Normalize for consistency: ./file.md instead of file.md for files in the same directory
    # Only add ./ if it's a file and not already starting with . or /
    if not relative_path.startswith(('.', '/')) and to_file.is_file():
        relative_path = './' + relative_path

    return relative_path + anchor


def fix_all_broken_links(broken_links: list[dict]):
    """Applies fixes to all identified broken links."""
    files_to_fix = defaultdict(list)
    for link_info in broken_links:
        files_to_fix[link_info['file']].append(link_info)

    fixed_count = 0
    for file_path, links_in_file in files_to_fix.items():
        try:
            original_content = file_path.read_text(encoding='utf-8')
            lines = original_content.splitlines()
        except IOError as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)
            continue

        links_in_file.sort(key=lambda x: x['line_number'], reverse=True)

        file_fixed_count = 0
        for link_info in links_in_file:
            line_idx = link_info['line_number'] - 1
            current_line = lines[line_idx]
            original_target_url = link_info['target_url']
            correct_absolute_path = link_info['correct_absolute_path']

            new_relative_path = get_relative_path(file_path, correct_absolute_path, original_target_url)

            if new_relative_path and new_relative_path != original_target_url:
                new_full_markdown_link = f"[{link_info['link_text']}]({new_relative_path})"
                start_col, end_col = link_info['start_col'], link_info['end_col']
                lines[line_idx] = current_line[:start_col] + new_full_markdown_link + current_line[end_col:]

                print(f"Fixed: {file_path.relative_to(ROOT)}:{link_info['line_number']} - '{original_target_url}' -> '{new_relative_path}'")
                file_fixed_count += 1
                fixed_count += 1

        if file_fixed_count > 0:
            updated_content = "\n".join(lines)
            try:
                file_path.write_text(updated_content, encoding='utf-8')
                print(f"Updated {file_path.relative_to(ROOT)} with {file_fixed_count} fixes.")
            except IOError as e:
                print(f"Error writing to file {file_path}: {e}", file=sys.stderr)

    print(f"\nTotal {fixed_count} links fixed across {len(files_to_fix)} files.")


def main():
    args = parse_args()

    if DEBUG_MODE:
        print(f"DEBUG: ROOT is {ROOT}")
        print(f"DEBUG: DOCS_DIR is {DOCS_DIR}")
        print(f"DEBUG: EXCLUDE_DIRS are {EXCLUDE_DIRS}")

    if not DOCS_DIR.is_dir():
        print(f"Error: 'docs' directory not found at {DOCS_DIR}", file=sys.stderr)
        sys.exit(1)

    all_project_md_files = list_files_recursive(ROOT, EXCLUDE_DIRS)

    if DEBUG_MODE:
        print(f"DEBUG: All project MD files found (after exclusion): {[p.relative_to(ROOT) for p in all_project_md_files]}")

    # Build maps for resolution
    filename_to_paths_map = defaultdict(list)  # e.g., 'README.md': [path1, path2]
    stem_to_paths_map = defaultdict(list)  # e.g., 'README': [path1, path2]

    for f in all_project_md_files:
        if f.name not in EXCLUDE_AMBIGUOUS_FILENAMES:
            filename_to_paths_map[f.name].append(f)
            stem_to_paths_map[f.stem].append(f)

    # Identify ambiguous files (those with same filename or stem in multiple locations)
    ambiguous_filenames = {name: paths for name, paths in filename_to_paths_map.items() if len(paths) > 1}
    ambiguous_stems = {stem: paths for stem, paths in stem_to_paths_map.items() if len(paths) > 1}

    if DEBUG_MODE:
        print(f"DEBUG: Filename to paths map: { {k: [p.relative_to(ROOT) for p in v] for k, v in filename_to_paths_map.items()} }")
        print(f"DEBUG: Stem to paths map: { {k: [p.relative_to(ROOT) for p in v] for k, v in stem_to_paths_map.items()} }")
        print(f"DEBUG: Ambiguous Filenames (from filename_to_paths_map): { {k: [p.relative_to(ROOT) for p in v] for k, v in ambiguous_filenames.items()} }")
        print(f"DEBUG: Ambiguous Stems (from stem_to_paths_map): { {k: [p.relative_to(ROOT) for p in v] for k, v in ambiguous_stems.items()} }")

    if ambiguous_filenames or ambiguous_stems:
        print("Warning: The following filenames/stems are ambiguous and cannot be reliably used in bare links (e.g., '[...](filename.md)').", file=sys.stderr)
        print("Please use explicit relative paths (e.g., '[...](./path/to/filename.md)') for these files to ensure correct resolution.", file=sys.stderr)
        if ambiguous_filenames:
            print("Ambiguous Filenames:", file=sys.stderr)
            for name, paths in sorted(ambiguous_filenames.items()):
                rel_paths = sorted([str(p.relative_to(ROOT)) for p in paths])
                print(f"- '{name}': found in", file=sys.stderr)
                for rel_path in rel_paths:
                    print(f"    - {rel_path}", file=sys.stderr)
        if ambiguous_stems:
            print("Ambiguous Stems:", file=sys.stderr)
            for stem, paths in sorted(ambiguous_stems.items()):
                rel_paths = sorted([str(p.relative_to(ROOT)) for p in paths])
                print(f"- '{stem}': found in", file=sys.stderr)
                for rel_path in rel_paths:
                    print(f"    - {rel_path}", file=sys.stderr)
        print("---", file=sys.stderr)

    broken_links = []
    canonical_issues = []
    link_count = 0

    # Only check links originating from files within DOCS_DIR
    md_files_to_check_links_from = [f for f in list_files_recursive(DOCS_DIR, EXCLUDE_DIRS) if f.suffix == '.md']

    for file in md_files_to_check_links_from:
        try:
            content = file.read_text(encoding='utf-8')
        except IOError as e:
            print(f"Warning: Could not read file {file}: {e}", file=sys.stderr)
            continue

        links = extract_links(content)
        link_count += len(links)

        for link_info in links:
            target_url = link_info['target_url']

            if is_external_link(target_url) or is_anchor(target_url) or target_url.startswith(('mailto:', 'tel:')):
                continue

            resolved_path = resolve_target(file, target_url, filename_to_paths_map, stem_to_paths_map)

            if not resolved_path or not resolved_path.exists():
                issue = {
                        **link_info,
                        'file':                   file,
                        'resolved_absolute_path': resolved_path,
                        'correct_absolute_path':  None,
                        'issue_type':             'missing-target',
                }
                broken_links.append(issue)
                continue

            if resolved_path.is_dir():
                index_md_path = resolved_path / 'index.md'
                readme_md_path = resolved_path / 'README.md'

                correct_target_path = None
                if index_md_path.is_file():
                    correct_target_path = index_md_path
                elif readme_md_path.is_file():
                    correct_target_path = readme_md_path

                if not correct_target_path:
                    issue = {
                            **link_info,
                            'file':                   file,
                            'resolved_absolute_path': resolved_path,
                            'correct_absolute_path':  None,
                            'issue_type':             'directory-without-index',
                    }
                    broken_links.append(issue)
                    continue

                ideal_relative_path = get_relative_path(file, correct_target_path, target_url)
                if target_url != ideal_relative_path:
                    issue = {
                            **link_info,
                            'file':                   file,
                            'resolved_absolute_path': resolved_path,
                            'correct_absolute_path':  correct_target_path,
                            'issue_type':             'canonical-mismatch',
                    }
                    canonical_issues.append(issue)
                continue

            correct_target_path = resolved_path
            ideal_relative_path = get_relative_path(file, correct_target_path, target_url)
            if target_url != ideal_relative_path:
                issue = {
                        **link_info,
                        'file':                   file,
                        'resolved_absolute_path': resolved_path,
                        'correct_absolute_path':  correct_target_path,
                        'issue_type':             'canonical-mismatch',
                }
                canonical_issues.append(issue)

    rel_docs = DOCS_DIR.relative_to(ROOT)

    if args.fix:
        if canonical_issues:
            print(f"\nFound {len(canonical_issues)} canonical link issues. Attempting to fix them...")
            fix_all_broken_links(canonical_issues)
        else:
            print("\nNo canonical link issues detected that can be auto-fixed.")

        if broken_links:
            print("\nThe following links remain unresolved and require manual attention:", file=sys.stderr)
            for b in sorted(broken_links, key=lambda x: (x['file'], x['line_number'])):
                rel_file = b['file'].relative_to(ROOT)
                resolved_display = 'N/A'
                if b['resolved_absolute_path'] and isinstance(b['resolved_absolute_path'], Path):
                    try:
                        resolved_display = b['resolved_absolute_path'].relative_to(ROOT)
                    except ValueError:
                        resolved_display = b['resolved_absolute_path']
                print(f"- {rel_file}:{b['line_number']} → '{b['target_url']}' (resolved: {resolved_display})", file=sys.stderr)

        print("\nFixing process completed. Please re-run the checker without --fix to verify.")
        exit_code = 1 if broken_links or (args.fail_on_style and canonical_issues) else 0
        sys.exit(exit_code)

    if canonical_issues:
        print(
                f"\nCanonical link suggestions ({len(canonical_issues)}) in {len(md_files_to_check_links_from)} files ({link_count} links scanned) under {rel_docs}/:",
                file=sys.stderr)
        for issue in sorted(canonical_issues, key=lambda x: (x['file'], x['line_number'])):
            rel_file = issue['file'].relative_to(ROOT)
            suggestion = get_relative_path(issue['file'], issue['correct_absolute_path'], issue['target_url']) if issue['correct_absolute_path'] else 'N/A'
            resolved_display = 'N/A'
            if issue['resolved_absolute_path'] and isinstance(issue['resolved_absolute_path'], Path):
                try:
                    resolved_display = issue['resolved_absolute_path'].relative_to(ROOT)
                except ValueError:
                    resolved_display = issue['resolved_absolute_path']
            print(f"- {rel_file}:{issue['line_number']} → '{issue['target_url']}' (resolved: {resolved_display}, suggested: '{suggestion}')", file=sys.stderr)

    if broken_links:
        print(f"\nBroken links found ({len(broken_links)}) in {len(md_files_to_check_links_from)} files ({link_count} links scanned) under {rel_docs}/:",
              file=sys.stderr)
        for b in sorted(broken_links, key=lambda x: (x['file'], x['line_number'])):
            rel_file = b['file'].relative_to(ROOT)
            resolved_display = 'N/A'
            if b['resolved_absolute_path'] and isinstance(b['resolved_absolute_path'], Path):
                try:
                    resolved_display = b['resolved_absolute_path'].relative_to(ROOT)
                except ValueError:
                    resolved_display = b['resolved_absolute_path']
            print(f"- {rel_file}:{b['line_number']} → '{b['target_url']}' (resolved: {resolved_display}, status: {b['issue_type']})", file=sys.stderr)

    if not canonical_issues and not broken_links:
        print(f"No broken local links found under {rel_docs}/. Scanned {len(md_files_to_check_links_from)} files and {link_count} links.")

    exit_code = 1 if broken_links or (args.fail_on_style and canonical_issues) else 0
    if canonical_issues and not broken_links and exit_code == 0:
        print("\nNote: canonical suggestions reported above but not treated as errors. Use --fail-on-style to escalate.")
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(2)
