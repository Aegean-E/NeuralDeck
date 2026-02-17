# NeuralDeck

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
</p>

---

**NeuralDeck** is a powerful desktop application that transforms your study materials—PDFs, Word documents, and PowerPoints—into high-quality Anki flashcards. By leveraging the power of local Large Language Models (LLMs), it offers a completely offline and private workflow, ensuring your data never leaves your computer.

It's designed for students, researchers, and lifelong learners who want to automate the tedious process of card creation without sacrificing control or privacy.

## Why NeuralDeck?

-   **🧠 Intelligent & Automated**: Go from a 300-page textbook to a ready-to-study Anki deck in minutes, not hours.
-   **🔒 100% Private**: All processing happens locally. Your documents and generated cards are never sent to the cloud.
-   **🤖 LLM-Powered**: Utilizes state-of-the-art local LLMs (like Llama 3, Mistral, or Phi-3 via LM Studio) to understand context and generate accurate, relevant questions.
-   **🔧 Fully Controllable**: A comprehensive UI allows you to review, edit, approve, or discard every single card before it's synced to Anki.
-   **🌐 Multi-Format Support**: Natively handles `.pdf`, `.docx`, `.pptx`, and `.txt` files.
-   **🔌 Seamless Anki Integration**: A custom Anki add-on provides a direct bridge for one-click synchronization.

## Core Features

-   **Local First Processing**: Connects to any OpenAI-compatible local server, with a default setup for LM Studio.
-   **Multi-Document Support**: Extracts text from PDF, Word (`.docx`), PowerPoint (`.pptx`), and plain text (`.txt`) files.
-   **Smart Deck Matching**: Automatically categorizes generated cards into your existing Anki decks. It analyzes the card's content and scores it against your deck names (e.g., a card about "myocardial infarction" will be routed to a "Cardiology" deck).
-   **AI Refinement Mode**: An optional second pass where the AI acts as an editor, correcting grammatical errors, improving question clarity, and ensuring consistency.
-   **High-Density Generation**: A special mode for deep, exhaustive learning. It forces the AI to extract every distinct fact, definition, and detail, which is ideal for complex subjects like medicine or law.
-   **Interactive Review & Edit**: A user-friendly interface to edit questions, answers, and deck assignments before syncing.
-   **Bulk Operations**: Check/uncheck all cards, add manual cards, and move multiple cards to a different deck at once.
-   **Session Persistence**: Your workspace is automatically saved. Close the app and resume your review session later without losing any generated cards.
-   **Resilient & Stable**: Built with failure isolation, the pipeline can handle corrupted document pages and unstable LLM responses without crashing.

## Prerequisites

- **Python 3.10+**
- **Anki** (Desktop Application)
- **A Local LLM Server**: LM Studio is recommended and works out-of-the-box. Any OpenAI-compatible API endpoint will work.

## Installation

### 1. Install NeuralDeck

1.  Clone the repository:
   ```bash
   git clone https://github.com/Aegean-E/NeuralDeck.git
   cd NeuralDeck
   ```

2.  Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Install the Anki Bridge Add-on

To allow NeuralDeck to communicate with Anki, you must install the included bridge add-on.

1.  Open **Anki**.
2.  Navigate to **Tools** > **Add-ons** > **View Files**.
3.  Create a new folder named `NeuralDeckBridge`.
4.  Copy the contents of the `anki_addon` folder (`__init__.py` and `manifest.json`) from this project into the new `NeuralDeckBridge` folder.
5.  **Restart Anki**.

When Anki restarts, the bridge will start automatically. You can verify this by checking the terminal where you launched Anki for a message like `NeuralDeck Bridge running on port 5005...`.

## Usage Guide

1.  **Start your Local LLM**: Open LM Studio, load a model (e.g., `Meta-Llama-3-8B-Instruct`), and start the Local Server on the `Chat Complications` tab.
2.  **Open Anki**: Ensure Anki is running in the background with the NeuralDeck Bridge active.
3.  **Run NeuralDeck**:
   ```bash
   python main.py
   ```
4.  **Generate Cards**:
    -   Click **Select Document** to choose your source file (`.pdf`, `.docx`, etc.).
    -   Select your target **Language** and choose which of your Anki decks the AI can assign cards to.
    -   Click **Generate Cards**.
5.  **Review & Sync**:
    -   As cards are generated, they will appear in the "Review" area.
    -   You can edit the text directly in the entry boxes or change the assigned deck from the dropdown.
    -   Use the checkboxes to **Approve** the cards you want to keep.
    -   Click **Sync Approved to Anki** to send them directly to your collection.

## Configuration Settings

All settings are accessible in the **Settings** tab and are saved automatically.

| Setting                 | Description                                                                                                                            | Default Value                               |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| **Theme**               | Changes the visual theme of the application.                                                                                           | `darkly`                                    |
| **API URL**             | The endpoint for your local LLM server.                                                                                                | `http://localhost:1234/v1/chat/completions` |
| **API Key**             | The API key for your server (LM Studio's default is `lm-studio`).                                                                      | `lm-studio`                                 |
| **Model Name**          | The model identifier to use for generation.                                                                                            | `local-model`                               |
| **Temperature**         | Controls the creativity of the AI (0.0 = deterministic, 1.0 = creative).                                                               | `0.7`                                       |
| **Card Density**        | `Low`: Big-picture concepts. `Medium`: Balanced. `High`: Exhaustive detail extraction.                                                 | `Medium`                                    |
| **Concurrency**         | Number of parallel threads to use for generation. Limited to your CPU core count to prevent system overload.                           | `1`                                         |
| **Filter 'Yes/No'**     | Automatically removes simple questions that can be answered with "Yes" or "No".                                                        | `True`                                      |
| **Smart Deck Matching** | Enables content-aware analysis to assign cards to the most relevant deck.                                                              | `True`                                      |
| **AI Refinement**       | Enables a second AI pass to review and edit generated cards for quality. Slower but produces better results.                           | `False`                                     |
| **Deterministic Mode**  | Disables parallelism and sets a fixed seed to ensure the same output for the same input file. Useful for testing.                      | `False`                                     |
| **Debug Mode**          | Enables verbose logging in the UI and `session.log` file for troubleshooting.                                                          | `False`                                     |
| **Custom Prompt**       | Add your own instructions to guide the AI's tone and focus (e.g., "Focus on clinical definitions", "Make questions difficult").          | `(empty)`                                   |

## Architecture

NeuralDeck operates as a modular system designed for local execution and seamless integration.

1.  **UI (`ui.py`)**: The main interface built with `ttkbootstrap`. It manages the user workflow, displays real-time logs, and handles concurrent processing threads to keep the UI responsive.
2.  **Document Processor (`document_processor.py`)**:
    -   **Ingestion**: Reads various document formats (`.pdf`, `.docx`, etc.).
    -   **Chunking**: Intelligently splits text into context-aware chunks that respect paragraph and sentence boundaries, optimized to fit the LLM's context window.
    -   **Generation**: Sends chunks to the Local LLM with a detailed system prompt that instructs it on formatting, language, and quality control.
    -   **Parsing**: Uses a robust JSON parser to reliably extract card objects even from malformed or noisy LLM outputs.
3.  **Anki Integration (`anki_addon/` & `anki_integration.py`)**:
    -   **NeuralDeck Bridge**: A lightweight HTTP server running inside Anki on port 5005. It exposes endpoints to get deck names and add new cards.
    -   **Communication**: The desktop app sends secure HTTP POST requests to the bridge. The bridge restricts requests to `localhost` to prevent unauthorized external access.

## Troubleshooting

### Anki Connection Failed
- **Symptoms**: "Could not connect to Anki" error when fetching decks or syncing.
- **Fix**:
  1. Ensure Anki is open and a profile is loaded.
  2. Verify the **NeuralDeck Bridge** add-on is installed and enabled in **Tools > Add-ons**.
  3. Check if another application is using port 5005. You can change the port in the add-on's config if needed.
  4. Restart Anki.

### PDF Text Not Found
- **Symptoms**: "No text could be extracted" error.
- **Cause**: The PDF is likely a scanned image without OCR.
- **Fix**: Use an OCR tool (like Adobe Acrobat, or free online services) to convert the scanned PDF to a text-selectable PDF before using it with NeuralDeck.

### LLM Connection Error
- **Symptoms**: "Connection Failed to http://localhost:1234..."
- **Fix**:
  1. Open LM Studio.
  2. Load a model.
  3. Navigate to the server tab (e.g., "Local Server" in LM Studio) and click **Start Server**.
  4. Ensure firewall is not blocking localhost connections.

## Building the Executable

To create a standalone executable for Windows:

1.  Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2.  Run the build command from the project root:
   ```bash
   pyinstaller --noconsole --onefile --name "NeuralDeck" main.py
   ```
3.  The executable (`NeuralDeck.exe`) will be located in the `dist/` folder.

## Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or code contributions, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the **GNU GPLv3 License**. See the LICENSE file for details.
