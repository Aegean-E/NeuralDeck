# NeuralDeck 0.2

<p align="center">
  <img src="https://github.com/Aegean-E/NeuralDeck/blob/main/banner.png?raw=true" alt="NeuralDeck Banner" width="1200">
</p>

<p align="center">
  <b>Your personal, privacy-focused AI assistant for creating Anki flashcards from any document.</b>
  <br />
  <br />
  <img alt="GitHub release (latest by date)" src="https://img.shields.io/github/v/release/Aegean-E/NeuralDeck">
  <img alt="GitHub" src="https://img.shields.io/github/license/Aegean-E/NeuralDeck">
  <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/Aegean-E/NeuralDeck">
  <img alt="Python versions" src="https://img.shields.io/badge/python-3.10+-blue.svg">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg">
</p>

---

## Table of Contents

1. [About](#about)
2. [Why NeuralDeck?](#why-neuraldeck)
3. [Features](#features)
4. [Quick Start](#quick-start)
5. [Installation](#installation)
   - [Prerequisites](#prerequisites)
   - [Setup NeuralDeck](#1-install-neuraldeck)
   - [Setup Anki Bridge](#2-setup-anki-bridge)
6. [Usage Guide](#usage-guide)
7. [Configuration Settings](#configuration-settings)
8. [Architecture](#architecture)
   - [Module Overview](#module-overview)
   - [Data Flow](#data-flow)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)
11. [Building the Executable](#building-the-executable)
12. [Security](#security)
13. [Contributing](#contributing)
14. [License](#license)

---

## About

**NeuralDeck** is a powerful desktop application that transforms your study materials—PDFs, Word documents, and PowerPoints—into high-quality Anki flashcards. By leveraging the power of local Large Language Models (LLMs), it offers a completely offline and private workflow, ensuring your data never leaves your computer.

It's designed for students, researchers, and lifelong learners who want to automate the tedious process of card creation without sacrificing control or privacy.

---

## Why NeuralDeck?

- **🧠 Intelligent & Automated**: Go from a 300-page textbook to a ready-to-study Anki deck in minutes, not hours.
- **🔒 100% Private**: All processing happens locally. Your documents and generated cards are never sent to the cloud.
- **🤖 LLM-Powered**: Utilizes state-of-the-art local LLMs (like Llama 3, Mistral, or Phi-3 via LM Studio) to understand context and generate accurate, relevant questions.
- **🔧 Fully Controllable**: A comprehensive UI allows you to review, edit, approve, or discard every single card before it's synced to Anki.
- **🌐 Multi-Format Support**: Natively handles `.pdf`, `.docx`, `.pptx`, and `.txt` files.
- **🔌 Seamless Anki Integration**: A custom Anki add-on provides a direct bridge for one-click synchronization.
- **⚡ High Performance**: Multi-threaded processing with intelligent concurrency control.
- **🛡️ Resilient**: Built with failure isolation to handle corrupted pages and unstable LLM responses gracefully.

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Local First Processing** | Connects to any OpenAI-compatible local server, with a default setup for LM Studio. |
| **Multi-Document Support** | Extracts text from PDF, Word (`.docx`), PowerPoint (`.pptx`), and plain text (`.txt`) files. |
| **Smart Deck Matching** | Automatically categorizes generated cards into your existing Anki decks by analyzing content. |
| **AI Refinement Mode** | Optional second AI pass for grammar correction, question clarity, and consistency. |
| **High-Density Generation** | Forces exhaustive detail extraction for complex subjects like medicine or law. |
| **Interactive Review & Edit** | User-friendly interface to edit questions, answers, and deck assignments before syncing. |
| **Bulk Operations** | Check/uncheck all cards, add manual cards, and move multiple cards to different decks. |
| **Session Persistence** | Workspace automatically saved. Resume your review session anytime. |
| **Resilient Pipeline** | Handles corrupted document pages and unstable LLM responses without crashing. |

### Advanced Features

- **Deterministic Mode**: Ensures reproducible output for testing and consistency.
- **Debug Mode**: Verbose logging for troubleshooting.
- **Custom Prompts**: Guide AI behavior with custom instructions.
- **Card Density Control**: Low (concepts), Medium (balanced), High (exhaustive).
- **Parallel Processing**: Configurable concurrency for faster generation.
- **Smart Filtering**: Automatic removal of Yes/No questions and duplicate content.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Aegean-E/NeuralDeck.git
cd NeuralDeck
pip install -r requirements.txt

# 2. Install Anki Bridge (see Installation section)

# 3. Run NeuralDeck
python main.py

# 4. Start LM Studio, load a model, start server on port 1234

# 5. Open Anki and enjoy!
```

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | Required for running the application |
| **Anki** | Desktop | Must be running for sync to work |
| **Local LLM Server** | - | LM Studio recommended |

### Recommended LLM Models

- **Meta-Llama-3-8B-Instruct** - Excellent general-purpose model
- **Mistral-7B-Instruct** - Fast and efficient
- **Phi-3-mini** - Lightweight option for older hardware
- Any OpenAI-compatible model via LM Studio, Ollama, or text-generation-webui

### 1. Install NeuralDeck

```bash
# Clone the repository
git clone https://github.com/Aegean-E/NeuralDeck.git
cd NeuralDeck

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Optional: Install development dependencies for testing
pip install pytest
```

### 2. Setup Anki Bridge

To allow NeuralDeck to communicate with Anki, install the included bridge add-on:

1. Open **Anki**
2. Navigate to **Tools** > **Add-ons** > **View Files**
3. Create a new folder named `NeuralDeckBridge`
4. Copy the contents of the `anki_addon` folder (`__init__.py` and `manifest.json`) from this project into the new folder
5. **Restart Anki**

> **Verification**: Look for `NeuralDeck Bridge running on port 5005...` in the Anki terminal output.

---

## Usage Guide

### Step 1: Start Your Local LLM

1. Open **LM Studio**
2. Download and load a model (e.g., `Meta-Llama-3-8B-Instruct`)
3. Navigate to the **Local Server** tab
4. Click **Start Server**
5. Default endpoint: `http://localhost:1234/v1/chat/completions`

### Step 2: Launch Anki

Ensure Anki is running with the NeuralDeck Bridge add-on active.

### Step 3: Run NeuralDeck

```bash
python main.py
```

### Step 4: Generate Cards

1. Click **Select Document** to choose your source file (`.pdf`, `.docx`, `.pptx`, `.txt`)
2. Select your target **Language** (e.g., English, Spanish, French)
3. Choose which Anki decks the AI can assign cards to (or let Smart Deck Matching handle it)
4. Configure **Card Density**:
   - **Low**: Big-picture concepts and key definitions
   - **Medium**: Balanced coverage of facts and concepts
   - **High**: Exhaustive detail extraction
5. Click **Generate Cards**

### Step 5: Review & Sync

- Cards appear in real-time in the Review area
- Edit questions/answers directly in the entry boxes
- Change assigned deck from the dropdown
- Check/uncheck cards to approve or discard
- Click **Sync Approved to Anki** to add cards to your collection

### Bulk Operations

- **Check All**: Select all generated cards
- **Uncheck All**: Deselect all cards
- **Add Manual Card**: Create custom cards manually
- **Move to Deck**: Bulk move selected cards to a different deck

---

## Configuration Settings

All settings are accessible in the **Settings** tab and are saved automatically to `config.json`.

| Setting | Description | Default |
|---------|-------------|---------|
| **Theme** | Visual theme (darkly, flatly, litera, etc.) | `darkly` |
| **API URL** | Local LLM server endpoint | `http://localhost:1234/v1/chat/completions` |
| **API Key** | Server authentication key | `lm-studio` |
| **Model Name** | Model identifier | `local-model` |
| **Temperature** | AI creativity (0.0=deterministic, 1.0=creative) | `0.7` |
| **Max Tokens** | Maximum tokens per response | `2048` |
| **Card Density** | Detail level: Low/Medium/High | `Medium` |
| **Concurrency** | Parallel threads (auto-limited to CPU cores) | `1` |
| **Filter 'Yes/No'** | Remove simple Yes/No questions | `True` |
| **Smart Deck Matching** | Content-aware deck assignment | `True` |
| **AI Refinement** | Second pass for quality improvement | `False` |
| **Deterministic Mode** | Fixed seed for reproducible output | `False` |
| **Debug Mode** | Verbose logging | `False` |
| **Custom Prompt** | Additional AI instructions | `(empty)` |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEURALDECK_CONFIG` | Custom config file path | `config.json` |
| `NEURALDECK_LOG` | Log file location | `session.log` |

---

## Architecture

### Module Overview

```
NeuralDeck/
├── main.py                 # Application entry point
├── ui.py                  # Main GUI (ttkbootstrap)
├── document_processor.py  # Document parsing & card generation
├── pipeline_utils.py      # Utilities (stats, validation, logging)
├── anki_integration.py   # HTTP client for Anki bridge
├── anki_addon/           # Anki-side add-on
│   ├── __init__.py       # Bridge server (port 5005)
│   └── manifest.json     # Add-on metadata
├── tests/                # Test suite (84 tests)
├── build.py              # PyInstaller build script
└── config.json           # User settings
```

### Detailed Module Documentation

#### `main.py`
Simple entry point that initializes and launches the GUI.

```python
from ui import AnkiGeneratorUI

def main():
    app = AnkiGeneratorUI()
    app.mainloop()
```

#### `ui.py` - User Interface
- **Framework**: ttkbootstrap (Bootstrap-styled Tkinter)
- **Features**:
  - Document selection and processing controls
  - Real-time log display
  - Interactive card review table
  - Settings panel with live updates
  - Concurrent thread management
  - Session state persistence

#### `document_processor.py` - Core Processing Engine

| Function | Description |
|----------|-------------|
| `extract_text_from_pdf()` | PDF text extraction with PyPDF2, handles encrypted/corrupt files |
| `_extract_text_from_docx()` | Word document parsing via python-docx |
| `_extract_text_from_pptx()` | PowerPoint extraction via python-pptx |
| `_extract_text_from_txt()` | Plain text file reading |
| `extract_text_from_document()` | Unified dispatcher for all formats |
| `check_llm_server()` | Connectivity check with fallback TCP probe |
| `call_lm_studio()` | LLM API client with SSE streaming support |
| `smart_chunk_text()` | Context-aware text splitting respecting boundaries |
| `robust_parse_objects()` | JSON extraction from LLM responses (handles noise/markdown) |
| `filter_and_process_cards()` | Card validation, deduplication, deck matching |
| `refine_generated_cards()` | AI-powered quality improvement pass |
| `generate_qa_pairs()` | Main pipeline orchestration with ThreadPoolExecutor |

#### `pipeline_utils.py` - Utilities

| Class | Description |
|-------|-------------|
| `PipelineStats` | Thread-safe metrics tracking (timing, counts, memory) |
| `FailureLogger` | JSONL logging of failed chunks and rejected cards |
| `CardValidator` | Card quality validation (length, duplicates, content) |
| `ResourceGuard` | File size and chunk count limits |

#### `anki_integration.py` - Desktop Client

| Function | Description |
|----------|-------------|
| `check_anki_connection()` | Ping Anki bridge server |
| `get_deck_names()` | Fetch deck list via HTTP GET |
| `create_anki_deck()` | Send cards via HTTP POST |

#### `anki_addon/__init__.py` - Anki Bridge Server

| Component | Description |
|-----------|-------------|
| `AnkiBridgeHandler` | HTTP request handler |
| `do_GET /get_decks` | Returns deck names from Anki collection |
| `do_POST /add_cards` | Creates cards in Anki |
| `do_OPTIONS` | CORS preflight handling |
| `add_cards_to_anki()` | Core card creation with model/deck management |
| Security | Path traversal prevention, localhost-only enforcement |

### Data Flow

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│  Document  │───▶│ Document Processor│───▶│ LLM Server │
│  (.pdf,    │    │ - Extraction     │    │ (LM Studio)│
│   .docx)   │    │ - Chunking       │    └──────┬──────┘
└─────────────┘    │ - Generation    │           │
                   └────────┬─────────┘           │
                            │ JSON               │
                            ▼                    │
                   ┌──────────────────┐           │
                   │ Card Validator  │◀──────────┘
                   │ - Filtering     │
                   │ - Deck Matching │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │    UI Display    │
                   │ - Review/Edit    │
                   │ - Approval       │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐    ┌────────┐
                   │ Anki Integration │───▶│  Anki  │
                   │ (HTTP POST)     │    │ Bridge │
                   └──────────────────┘    └────────┘
```

---

## Testing

NeuralDeck includes a comprehensive test suite covering all core modules.

### Running Tests

```bash
# Run all tests
py -m pytest tests/ -v

# Or use the test runner
python run_tests.py
python tests/run_tests.py

# Run specific test file
py -m pytest tests/test_document_processor.py -v

# Run with coverage
py -m pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

| Module | Test File | Coverage |
|--------|----------|----------|
| Anki Integration | `test_anki_integration.py`, `test_anki_integration_get_deck_names.py` | ✓ |
| Anki Addon | `test_anki_addon_logic.py`, `test_anki_addon_media.py` | ✓ |
| Document Processor | `test_document_processor.py`, `test_document_processor_extra.py` | ✓ |
| Pipeline Utils | `test_pipeline_utils.py` | ✓ |
| Full Pipeline | `test_pipeline.py` | ✓ |
| Failure Isolation | `test_failure_isolation.py` | ✓ |
| Deterministic Mode | `test_deterministic.py` | ✓ |

**Total: 84 tests**

---

## Troubleshooting

### Anki Connection Failed

**Symptoms**: "Could not connect to Anki" error when fetching decks or syncing.

**Solutions**:
1. Ensure Anki is open and a profile is loaded
2. Verify the **NeuralDeck Bridge** add-on is installed in **Tools > Add-ons**
3. Check if port 5005 is available:
   ```bash
   netstat -an | grep 5005
   ```
4. Change port in add-on config if needed
5. Restart Anki

### PDF Text Not Found

**Symptoms**: "No text could be extracted" error.

**Cause**: PDF is likely a scanned image without OCR.

**Solutions**:
1. Use OCR tools (Adobe Acrobat, PDF24, or online services)
2. Convert to text-selectable PDF before processing
3. Try a different PDF source

### LLM Connection Error

**Symptoms**: "Connection Failed to http://localhost:1234..."

**Solutions**:
1. Open LM Studio and verify model is loaded
2. Start the Local Server (not just Chat)
3. Check firewall rules for localhost
4. Verify API URL matches LM Studio settings

### Memory Issues with Large Files

**Symptoms**: Application slows down or crashes.

**Solutions**:
1. Reduce **Concurrency** to 1
2. Use **Low** Card Density
3. Split large documents into smaller files

### Cards Not Appearing in Correct Deck

**Symptoms**: Cards sync but go to wrong deck.

**Solutions**:
1. Disable **Smart Deck Matching** for manual assignment
2. Check deck names in Anki for exact matches
3. Review card deck assignment in UI before sync

---

## Building the Executable

### Using PyInstaller

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --noconsole --onefile --name "NeuralDeck" main.py

# Or use the build script
python build.py
```

The executable will be created in `dist/NeuralDeck-0.2/`.

### Using Build Script (Recommended)

The `build.py` script automatically includes ttkbootstrap assets:

```bash
python build.py
```

Output: `dist/NeuralDeck-0.2/NeuralDeck-0.2.exe`

### Build Requirements

- Windows 10+ (for .exe)
- Python 3.10+
- All requirements installed

---

## Security

- **Local-Only Processing**: All document processing happens on your machine
- **No Cloud Services**: Zero data leaves your computer
- **Localhost Communication**: Anki bridge restricts to 127.0.0.1 only
- **Path Traversal Protection**: Media file handling includes security checks
- **Input Validation**: Card content is validated before Anki submission

### Data Privacy

| Data | Location | Encryption |
|------|----------|------------|
| Documents | RAM only | N/A |
| Generated Cards | `session_cache.json` | None |
| Settings | `config.json` | None |
| Logs | `session.log` | None |

**Recommendation**: Clear `session_cache.json` after syncing sensitive content.

---

## Contributing

Contributions are welcome! Here's how you can help:

### Reporting Issues

1. Check existing issues before creating new ones
2. Include steps to reproduce
3. Attach relevant logs (enable Debug Mode)
4. Specify OS, Python version, and Anki version

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit pull request

### Development Setup

```bash
# Clone and setup
git clone https://github.com/Aegean-E/NeuralDeck.git
cd NeuralDeck

# Create virtual environment
python -m venv dev
dev\Scripts\activate  # Windows
source dev/bin/activate  # Linux/macOS

# Install all dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# Run tests
python -m pytest tests/ -v
```

---

## License

This project is licensed under the **Apache License Version 2.0, January 2004**. See the LICENSE file for details.

---

<p align="center">
  <sub>Built with ❤️ for learners everywhere</sub>
</p>
