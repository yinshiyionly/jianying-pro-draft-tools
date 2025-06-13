#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

# Define directories to create
directories = [
    "config",
    "ui/components",
    "services",
    "models",
    "utils",
    "workers",
    "handlers",
    "resources/icons",
    "resources/styles",
    "resources/sounds"
]

# Create directories
for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

print("Directory structure setup complete!")

# Create __init__.py files in each package directory
for directory in directories:
    if "/" in directory:
        # Handle nested directories
        parts = directory.split("/")
        current_path = ""
        for part in parts:
            current_path = os.path.join(current_path, part)
            init_file = os.path.join(current_path, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    f.write("# Package initialization\n")
                print(f"Created: {init_file}")
    else:
        # Handle top-level directories
        init_file = os.path.join(directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Package initialization\n")
            print(f"Created: {init_file}")

print("Package initialization files created!") 