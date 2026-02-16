# NeuralDeck 0.1 - Local LLM Anki Cards Generator

<p align="center">
  <img src="https://github.com/Aegean-E/NeuralDeck/blob/main/banner.png?raw=true" alt="NeuralDeck Banner" width="1200">
</p>

A local, privacy-focused desktop application that generates high-quality Anki flashcards from PDF documents using Local LLMs (like Llama 3 via LM Studio). It features a custom Anki add-on for seamless synchronization, smart deck matching, and AI-powered refinement.

## Features

- **Local Processing**: Uses LM Studio or OpenAI-compatible local servers. No data is sent to the cloud.
- **PDF Extraction**: Intelligent text extraction and chunking from PDF files.
- **Smart Deck Matching**: Automatically categorizes cards into your existing Anki decks based on content.
- **AI Refinement**: A two-pass system where the AI reviews and polishes generated cards for accuracy and formatting.
- **Direct Anki Sync**: Pushes approved cards directly to Anki via a bundled add-on.
- **High Density Mode**: Extracts exhaustive clinical details (ideal for medical/law students).
- **Parallel Processing**: Multi-threaded generation for faster results.

## Prerequisites

- **Python 3.10+**
- **Anki** (Desktop Application)
- **LM Studio** (or any local LLM server running on port 1234)

## Installation

### 1. Install the Desktop Application

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/AIAnkiCardsGenerator.git
   cd AIAnkiCardsGenerator
   ```

2. Install dependencies:
   ```bash
   pip install ttkbootstrap PyPDF2
   ```

### 2. Install the Anki Add-on

To allow the app to communicate with Anki, you must install the included bridge add-on.

1. Open **Anki**.
2. Navigate to **Tools** > **Add-ons** > **View Files**.
3. Create a new folder named `LocalAIAnkiCardsBridge`.
4. Copy the contents of the `anki_addon` folder (`__init__.py` and `manifest.json`) from this project into that new folder.
5. **Restart Anki**. You should see a notification that the "Anki Bridge" is running on port 5005.

**Note:** The add-on is compatible with both modern Anki (2.1.50+) and older versions.

## Usage

1. **Start your Local LLM**: Open LM Studio, load a model (e.g., `Meta-Llama-3-8B-Instruct`), and start the Local Server.
2. **Open Anki**: Ensure it is running in the background.
3. **Run the Generator**:
   ```bash
   python main.py
   ```
4. **Generate Cards**:
   - Click **Select PDF** to choose your source document.
   - Select your target **Language**.
   - Click **Generate Cards**.
5. **Review & Sync**:
   - The app will generate cards in batches.
   - Review them in the list. You can edit the text or change the deck.
   - Click **Approve** (or "Check All") for the cards you want to keep.
   - Click **Sync Approved to Anki** to send them to your decks.

## Configuration

Go to the **Settings** tab to customize:

- **AI Server**: Change URL/API Key if not using LM Studio default.
- **Card Density**:
  - *Low*: Big picture concepts.
  - *High*: Exhaustive extraction (splits lists into multiple cards).
- **Concurrency**: Increase to process multiple text chunks simultaneously (requires a strong GPU).
- **AI Refinement**: Enable for a second pass where AI fixes grammar and formatting (slower but higher quality).
- **Debug Mode**: Enable verbose logging to troubleshoot LLM connection or parsing issues.
- **Deterministic Mode**: Enable for reproducible output (fixed seed, sequential processing).

## Architecture & Workflow

NeuralDeck operates as a modular system designed for local execution and seamless integration.

### 1. Document Processing (`document_processor.py`)
- **Ingestion**: Reads PDF files using `PyPDF2`.
- **Chunking**: Splits text into context-aware chunks (respecting paragraphs and sentences) to fit within the LLM's context window.
- **Generation**: Sends chunks to the Local LLM (via LM Studio API) with prompt instructions for formatting (JSON) and content extraction.
- **Parsing**: Uses a robust JSON parser to extract card objects even from malformed LLM outputs.

### 2. User Interface (`ui.py`)
- Built with `ttkbootstrap` (modern Tkinter).
- Manages the review workflow (Approve/Reject/Edit).
- Handles concurrent processing threads to keep the UI responsive.
- Displays real-time logs and progress.

### 3. Anki Integration (`anki_addon/` & `anki_integration.py`)
- **Bridge Add-on**: A lightweight HTTP server running inside Anki on port 5005.
- **Communication**: The desktop app sends HTTP POST requests to the bridge to add cards.
- **Security**: The bridge restricts requests to `localhost` to prevent unauthorized external access.

## Reliability & Failure Handling

NeuralDeck has been hardened to handle common issues:
- **PDF Extraction**: Skips corrupted or empty pages gracefully with a warning, instead of crashing.
- **LLM Stability**: Retries connection on transient errors and filters out invalid JSON/Markdown artifacts.
- **Concurrency**: Automatically limits parallel workers to your system's CPU count to prevent freezing.
- **Anki Sync**: Verifies connection before syncing to prevent data loss.

## New Features

### Deterministic Generation Mode
NeuralDeck now includes a **Deterministic Mode** for reproducible results.
- **Fixed Seeding**: Sets random seeds to ensure consistent output for the same input.
- **Sequential Processing**: Disables parallelism to guarantee chunk order and eliminate race conditions.
- **No Shuffling**: Disables deck shuffling to ensure LLM deck assignment is consistent.

### Performance Metrics & Profiling
The application now tracks detailed metrics during generation:
- **Extraction Time**: Time taken to read and parse the PDF.
- **Chunking Time**: Time taken to split text into manageable parts.
- **LLM Processing Time**: Cumulative time spent waiting for the AI.
- **Throughput**: Cards generated per second and total duration.
A summary report is displayed in the logs upon completion.

### Failure Isolation System
The pipeline is designed to be resilient:
- **Chunk-Level Isolation**: If a single text chunk fails (e.g., LLM network error, malformed response), it is logged to `failed_chunks_log.jsonl`, but the rest of the document continues processing.
- **Card Validation**: Generated cards are validated for minimum content length and quality. Rejected cards are logged to `rejected_cards_log.jsonl`.
- **Resource Guard**: Prevents processing of excessively large files or chunk counts to protect system memory.

### Quality Validation Rules
Each generated card passes through a `CardValidator`:
- **Non-Empty**: Must have valid Question and Answer.
- **Minimum Length**: Question > 10 chars, Answer > 3 chars.
- **No Duplicates**: Duplicate questions within the same session are automatically filtered.
- **Safety**: "Yes/No" answers are filtered out (configurable).

## Troubleshooting

### Anki Connection Failed
- **Symptoms**: "Could not connect to Anki" error when clicking "Sync".
- **Fix**:
  1. Ensure Anki is open.
  2. Verify the "Anki Bridge" add-on is installed (Tools > Add-ons).
  3. Check if another application is using port 5005.
  4. Restart Anki.

### PDF Text Not Found
- **Symptoms**: "No text could be extracted" error.
- **Cause**: The PDF is likely a scanned image without OCR.
- **Fix**: Use an OCR tool (like Adobe Acrobat or online converters) to convert the scanned PDF to a text-selectable PDF before using NeuralDeck.

### LLM Connection Error
- **Symptoms**: "Connection Failed to http://localhost:1234..."
- **Fix**:
  1. Open LM Studio.
  2. Load a model.
  3. Start the "Local Server" on port 1234.
  4. Ensure firewall is not blocking localhost connections.

### "PyPDF2 module not found"
- **Fix**: Run `pip install PyPDF2` in your terminal.

## Project Structure

- `main.py`: Entry point.
- `ui.py`: Tkinter-based GUI logic.
- `document_processor.py`: PDF extraction, chunking, and LLM interaction logic.
- `pipeline_utils.py`: Metrics, validation, and logging utilities.
- `anki_integration.py`: HTTP client for communicating with the Anki add-on.
- `anki_addon/`: Source code for the Anki plugin.

## Building the Executable (.exe)

To create a standalone executable for Windows:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Run the build command:
   ```bash
   pyinstaller --noconsole --onefile --name "NeuralDeck" main.py
   ```
3. The executable will be located in the `dist/` folder.

## License

GNU GPLv3 License
