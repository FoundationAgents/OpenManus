# OpenManus IDE - GUI User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Main Window Overview](#main-window-overview)
4. [Components](#components)
5. [Project Management](#project-management)
6. [Settings & Preferences](#settings--preferences)
7. [Keyboard Shortcuts](#keyboard-shortcuts)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

## Introduction

Welcome to OpenManus IDE! This is a comprehensive agent development environment with a GUI-first architecture designed for ease of use and productivity.

### Key Features

- **GUI-First Design**: The IDE is designed for visual interaction with progressive component loading
- **Component Auto-Discovery**: Automatically discovers and loads available panels
- **Reactive State Management**: All changes propagate through a central state manager
- **Message Bus**: Decoupled components communicate via a unified message bus
- **Progressive Loading**: UI renders immediately, components load in background
- **User-Friendly Errors**: Clear error messages with suggestions (no stack traces)
- **Customizable**: Themes, layouts, keyboard shortcuts all configurable

## Getting Started

### Installation

1. **Prerequisites**:
   ```bash
   Python 3.11-3.13
   PyQt6
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the GUI**:
   ```bash
   python main_gui.py
   ```

### First Run

On first run, you'll see:

1. **Splash Screen**: Shows while components are loading
2. **Component Discovery**: The application discovers available panels
3. **Progressive Loading**: Components load one by one
4. **Main Window**: Opens when all components are ready

### Quick Start Tutorial

1. **Create a New Project**:
   - Click `File > New Project`
   - Enter project name and location
   - Click `Create`

2. **Open a File**:
   - Click `File > Open` or `Ctrl+O`
   - Select a file
   - File opens in the code editor

3. **Configure Settings**:
   - Click `Tools > Settings` or `Alt+S`
   - Adjust preferences
   - Click `Apply` or `Save`

## Main Window Overview

### Window Layout

```
┌─────────────────────────────────────────────────────────┐
│ Menu Bar                                                │
├─────────────────────────────────────────────────────────┤
│ Toolbar                                                 │
├──────────┬────────────────────────────┬─────────────────┤
│          │                            │                 │
│  Left    │     Central Editor         │  Right Panels   │
│  Panels  │                            │  - Agent Control│
│  - Backup│                            │  - Workflow     │
│  - Resources                          │  - Monitor      │
│          │                            │  - Security     │
│          │                            │                 │
├──────────┴────────────────────────────┴─────────────────┤
│  Bottom Panels                                          │
│  - Command Log                                          │
│  - Console                                              │
└─────────────────────────────────────────────────────────┘
│ Status Bar                                              │
└─────────────────────────────────────────────────────────┘
```

### Menu Bar

- **File**: New, Open, Save, Exit
- **View**: Layout, Theme, Panel Visibility
- **Window**: Toggle panels, arrange windows
- **Tools**: Settings, Workspace, Command Validation
- **Help**: About, Documentation

### Toolbar

Quick access to common actions:
- New File
- Open File
- Save File
- Workspace Selector
- Refresh

### Status Bar

Shows:
- Current status messages
- Component loading progress
- Error notifications

## Components

### Central Editor

The main code editing area with:
- Syntax highlighting
- Line numbers
- Code execution
- File management

**Usage**:
- Type code directly
- Execute with `Ctrl+Enter`
- Save with `Ctrl+S`

### Agent Control Panel

Manage and control agents:
- Start/stop agents
- Configure agent parameters
- Monitor agent status

### Workflow Visualizer

Visualize and manage workflows:
- View workflow graphs
- Track execution progress
- Debug workflow issues

### Command Log

View all executed commands:
- Command history
- Execution timestamps
- Success/error status

### Console

Interactive console for:
- Running commands
- Viewing output
- Debugging

### Agent Monitor

Real-time agent monitoring:
- Active agents list
- Performance metrics
- Error tracking

### Security Monitor

Security and validation:
- Command validation
- Permission requests
- Security alerts

### Knowledge Graph

Visualize and navigate:
- Knowledge relationships
- Entity connections
- Graph queries

### Backup Management

Manage backups:
- Create backups
- Restore from backup
- View backup history

### Resource Catalog

Browse and manage resources:
- Files
- APIs
- Tools
- Templates

## Project Management

### Creating a New Project

1. Click `File > New Project`
2. Enter project details:
   - **Name**: Project name
   - **Location**: Where to create the project
   - **Description**: Optional project description
3. Click `Create`

### Opening an Existing Project

1. Click `File > Open Project`
2. Navigate to project directory
3. Select and open

### Recent Projects

Access recently opened projects:
- View in Project Manager panel
- Double-click to open
- Shows last 10 projects

### Project Structure

Each project contains:
```
MyProject/
├── .openmanus_project.json  # Project metadata
├── src/                     # Source code
├── data/                    # Data files
└── docs/                    # Documentation
```

## Settings & Preferences

Access via `Tools > Settings` or `Alt+S`.

### General Settings

- **Workspace**: Default workspace directory
- **Auto-save**: Automatically save files

### Appearance Settings

- **Theme**: Light or Dark
- **Font Family**: Editor font
- **Font Size**: Text size (8-24pt)
- **Line Numbers**: Show/hide line numbers
- **Syntax Highlighting**: Enable/disable

### LLM Settings

- **Model**: LLM model name
- **Base URL**: API endpoint
- **API Key**: Authentication key
- **Temperature**: Sampling temperature (0.0-2.0)
- **Max Tokens**: Maximum tokens per request

### Component Settings

Select which components to load at startup:
- Check components you want enabled
- Uncheck to disable
- Restart required for changes

### Advanced Settings

- **Log Level**: DEBUG, INFO, WARNING, ERROR
- **Max History**: History size

## Keyboard Shortcuts

### File Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New File |
| `Ctrl+O` | Open File |
| `Ctrl+S` | Save File |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Q` | Quit Application |

### Editing

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+X` | Cut |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+F` | Find |
| `Ctrl+H` | Replace |

### Navigation

| Shortcut | Action |
|----------|--------|
| `Tab` | Switch between panels |
| `Ctrl+Tab` | Next panel |
| `Ctrl+Shift+Tab` | Previous panel |

### Application

| Shortcut | Action |
|----------|--------|
| `Alt+S` | Open Settings |
| `Alt+N` | New Task |
| `F1` | Help |
| `F5` | Refresh |
| `F11` | Toggle Fullscreen |

### Customization

Customize shortcuts in Settings > Advanced > Keyboard Shortcuts.

## Troubleshooting

### Application Won't Start

**Problem**: Application fails to launch

**Solutions**:
1. Check Python version (3.11-3.13 required)
2. Verify PyQt6 is installed: `pip install PyQt6`
3. Check logs in `~/.openmanus/logs/gui.log`

### Component Failed to Load

**Problem**: "Component X failed to load"

**Solutions**:
1. Check error message for missing dependencies
2. Install missing dependencies: `pip install <package>`
3. Restart the application
4. Disable the component in Settings if not needed

### LLM Connection Failed

**Problem**: "Unable to connect to LLM endpoint"

**Solutions**:
1. Check internet connection
2. Verify API endpoint in Settings > LLM
3. Check API key is correct
4. Test with a different endpoint

### UI Freezing

**Problem**: Application becomes unresponsive

**Solutions**:
1. Wait for background operations to complete
2. Check Task Manager for high CPU usage
3. Reduce number of enabled components
4. Increase system resources

### File Operations Fail

**Problem**: Cannot open/save files

**Solutions**:
1. Check file permissions
2. Verify path exists
3. Ensure disk space available
4. Check for file locks

## FAQ

### Q: How do I switch between Light and Dark theme?

**A**: Go to `View > Theme` or `Settings > Appearance > Theme`.

### Q: Can I use the CLI instead of GUI?

**A**: Yes! Use `python main_cli.py --help` for CLI options. GUI is recommended for interactive use.

### Q: Where are my projects stored?

**A**: By default in `~/OpenManusProjects`. Change in Settings > General > Workspace.

### Q: How do I disable a component?

**A**: Settings > Components > Uncheck the component > Restart.

### Q: Can I customize keyboard shortcuts?

**A**: Yes, in Settings > Advanced > Keyboard Shortcuts (feature in development).

### Q: Where are logs stored?

**A**: In `~/.openmanus/logs/gui.log`.

### Q: How do I report a bug?

**A**: Check GitHub Issues or create a new issue with:
- Steps to reproduce
- Expected vs actual behavior
- Log files
- System information

### Q: Can I create custom panels?

**A**: Yes! Use the plugin architecture (see Plugin Development Guide).

### Q: How do I update the application?

**A**: Pull latest from Git and restart:
```bash
git pull origin main
python main_gui.py
```

### Q: Is there a mobile version?

**A**: Not currently. GUI is desktop-only (Windows/macOS/Linux).

### Q: Can I use multiple LLM endpoints?

**A**: Yes, configure fallback endpoints in Settings > LLM.

## Additional Resources

- **GitHub**: [OpenManus Repository](https://github.com/openmanus/openmanus)
- **Documentation**: `/docs` directory
- **Examples**: `/examples` directory
- **Community**: Join our Discord/Slack

## Getting Help

If you need help:
1. Check this guide
2. Review logs in `~/.openmanus/logs/`
3. Search GitHub Issues
4. Ask in community forums
5. Create a new issue with details

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**License**: See LICENSE file
