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

## Reliability & Failure Handling

NeuralDeck has been hardened to handle common issues:
- **PDF Extraction**: Skips corrupted or empty pages gracefully with a warning, instead of crashing.
- **LLM Stability**: Retries connection on transient errors and filters out invalid JSON/Markdown artifacts.
- **Concurrency**: Automatically limits parallel workers to your system's CPU count to prevent freezing.
- **Anki Sync**: Verifies connection before syncing to prevent data loss.

## New Features & Architecture

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
- **Chunk-Level Isolation**: If a single text chunk fails (e.g., LLM network error, malformed response), it is logged to `failed_chunks_log.json`, but the rest of the document continues processing.
- **Card Validation**: Generated cards are validated for minimum content length and quality. Rejected cards are logged to `rejected_cards_log.json`.
- **Resource Guard**: Prevents processing of excessively large files or chunk counts to protect system memory.

### Quality Validation Rules
Each generated card passes through a `CardValidator`:
- **Non-Empty**: Must have valid Question and Answer.
- **Minimum Length**: Question > 10 chars, Answer > 3 chars.
- **No Duplicates**: Duplicate questions within the same session are automatically filtered.
- **Safety**: "Yes/No" answers are filtered out (configurable).

### Testing & Mock System
NeuralDeck includes a comprehensive test suite with mocks for external dependencies:
- **MockLLM**: Simulates LLM responses for deterministic testing without a running server.
- **MockAnki**: Simulates Anki bridge for integration testing.
- **Integration Tests**: `tests/test_deterministic.py` and `tests/test_failure_isolation.py` ensure core reliability.

Run tests with:
```bash
python -m unittest discover tests
```

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
