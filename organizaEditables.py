import os
import shutil
import tkinter as tk
from tkinter import filedialog

def move_editable_files(source_folder):
    editables_folder = os.path.join(source_folder, "editables")
    if not os.path.exists(editables_folder):
        os.makedirs(editables_folder)

    # Recursively walk through all folders and subfolders
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith(('.ai', '.eps')):
                source_file_path = os.path.join(root, file)
                destination_file_path = os.path.join(editables_folder, file)
                # Move the file to the editables folder
                shutil.move(source_file_path, destination_file_path)
                print(f"Moved {file} to {editables_folder}")

def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Prompt the user to select a directory
    folder_selected = filedialog.askdirectory(title="Select Folder Containing .ai and .eps Files")

    if folder_selected:
        move_editable_files(folder_selected)
        print("Files moved successfully.")

if __name__ == "__main__":
    select_folder()
