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

## Project Structure

- `main.py`: Entry point.
- `ui.py`: Tkinter-based GUI logic.
- `document_processor.py`: PDF extraction, chunking, and LLM interaction logic.
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
