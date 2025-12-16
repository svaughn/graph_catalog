#!/bin/bash

# Check if .venv directory exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment at .venv..."
    python3 -m venv .venv
    
    if [ $? -eq 0 ]; then
        echo "Virtual environment created successfully!"
    else
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
else
    echo "Virtual environment already exists at .venv"
fi

# Activate the virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated!"
else
    echo "Error: Could not find activation script."
    exit 1
fi

# Install packages from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    echo "Found requirements.txt, installing packages..."
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo "Packages installed successfully!"
    else
        echo "Warning: Some packages may have failed to install"
    fi
else
    echo "No requirements.txt found, skipping package installation"
fi

echo ""
echo "Setup complete! Virtual environment is active."
