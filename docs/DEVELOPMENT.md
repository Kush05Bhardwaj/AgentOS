# Development Setup

AgentOS targets Python 3.11+ and is designed to be developed and tested on Windows and Linux. The current implementation is a foundation scaffold: it provides a CLI and static agent profile metadata, not model calls or autonomous execution yet.

## Prerequisites

- Python 3.11 or newer.
- Git.
- A terminal on Windows or Linux.

## Install for development

### Windows (PowerShell)

    git clone https://github.com/Kush05Bhardwaj/AgentOS.git
    Set-Location AgentOS
    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    .\.venv\Scripts\python.exe -m pytest
    .\.venv\Scripts\agentos.exe --help

### Linux

    git clone https://github.com/Kush05Bhardwaj/AgentOS.git
    cd AgentOS
    python3.11 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e ".[dev]"
    .venv/bin/python -m pytest
    .venv/bin/agentos --help

## Useful commands

    agentos --help
    agentos --version
    agentos agents
    agentos status

The commands currently available are deliberately small and do not require a model API key. Providers, orchestration, configuration loading, and tool execution will be introduced in later milestones.

## Quality checks

    python -m pytest
    ruff check .
    ruff format --check .

Run the platform-appropriate Python executable from the virtual environment if it is not activated. Pull requests are expected to pass both Linux and Windows CI.
