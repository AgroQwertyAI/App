import os
import pyperclip
from pathlib import Path

def get_ts_files_with_content():
    ts_files = []
    cwd = Path.cwd()
    
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.ts'):
                file_path = Path(root) / file
                try:
                    # Handle special directory names and relative paths
                    relative_path = os.path.relpath(file_path, cwd)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ts_files.append(f"// File: {relative_path}\n{content}\n")
                except Exception as e:
                    ts_files.append(f"// File: {file_path} (Error reading: {str(e)})\n")
    return '\n'.join(ts_files)

def main():
    try:
        combined_content = get_ts_files_with_content()
        if not combined_content.strip():
            print("No .ts files found in current directory and subdirectories.")
            return
            
        pyperclip.copy(combined_content)
        line_count = len(combined_content.splitlines())
        file_count = combined_content.count("// File:")
        print(f"Copied {line_count} lines from {file_count} .ts files to clipboard.")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()