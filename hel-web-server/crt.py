import os

def create_project_structure(base_path="hel-web-server"):
    """
    Creates the folder and file structure for the Hel-Web-Server project.
    """
    
    print(f"Creating project structure at: {os.path.abspath(base_path)}\n")

    # Define the core files and folders
    core_files = [
        "hel_web_server.py",
        "README.md",
        "LICENSE",
        "requirements.txt"
    ]

    folders = [
        "gui",
        "gui/resources",
        "server_manager",
        "utils"
    ]

    # Define files within specific folders
    folder_files = {
        "gui": ["main_window.py"],
        "gui/resources": ["icon.png"], # Placeholder for an icon file
        "server_manager": ["__init__.py", "web_server.py", "config.py"],
        "utils": ["__init__.py", "file_selector.py", "process_handler.py"]
    }

    # 1. Create the base directory if it doesn't exist
    if not os.path.exists(base_path):
        os.makedirs(base_path)
        print(f"Created base directory: {base_path}")
    else:
        print(f"Base directory already exists: {base_path}")
        # Optional: Ask user if they want to overwrite/continue
        # For simplicity, we'll proceed assuming it's okay.

    os.chdir(base_path) # Change current directory to the base path

    # 2. Create folders
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
        else:
            print(f"Folder already exists: {folder}")

    # 3. Create core files
    for file_name in core_files:
        if not os.path.exists(file_name):
            with open(file_name, 'w') as f:
                # Add basic content to some files
                if file_name == "requirements.txt":
                    f.write("PyQt5\n")
                elif file_name == "README.md":
                    f.write("# Hel-Web-Server\n\nA simple web server utility for Helwan Linux.\n")
                else:
                    f.write("") # Create empty file
            print(f"Created file: {file_name}")
        else:
            print(f"File already exists: {file_name}")

    # 4. Create files within specific folders
    for folder, files in folder_files.items():
        for file_name in files:
            file_path = os.path.join(folder, file_name)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    # Add basic content to __init__.py files
                    if file_name == "__init__.py":
                        f.write("# This file makes Python treat the directory as a package.\n")
                    elif file_name == "main_window.py":
                        f.write("from PyQt5.QtWidgets import QMainWindow, QApplication\n\n# Your main window class will go here\n")
                    elif file_name == "web_server.py":
                        f.write("import http.server\nimport socketserver\n\n# Server logic will go here\n")
                    elif file_name == "config.py":
                        f.write("DEFAULT_PORT = 8000\n")
                    else:
                        f.write("") # Create empty file
                print(f"Created file: {file_path}")
            else:
                print(f"File already exists: {file_path}")
    
    os.chdir("..") # Change back to original directory

    print("\nProject structure created successfully!")

if __name__ == "__main__":
    create_project_structure()
