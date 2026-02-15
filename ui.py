import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from ttkbootstrap.widgets import ToolTip
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import os
import json
from document_processor import extract_text_from_pdf, generate_qa_pairs
from anki_integration import create_anki_deck, get_deck_names

CONFIG_FILE = "config.json"

class CardReviewRow(ttk.Frame):
    """A row representing a single generated card for review."""
    def __init__(self, parent, question, answer, assigned_deck, available_decks, quote="", on_remove=None):
        super().__init__(parent)
        self.quote = quote
        self.on_remove = on_remove
        self.pack(fill=X, pady=5, padx=5)
        
        # Layout columns
        self.columnconfigure(1, weight=1) # Question/Answer area stretches
        
        # Checkbox for approval
        self.approved_var = ttk.BooleanVar(value=False)
        self.checkbox = ttk.Checkbutton(self, text="Approve", variable=self.approved_var, bootstyle="round-toggle")
        self.checkbox.grid(row=0, column=0, rowspan=2, padx=10, sticky="ns")
        
        # Inputs
        self.q_entry = ttk.Entry(self)
        self.q_entry.insert(0, question)
        self.q_entry.grid(row=0, column=1, sticky=EW, padx=5, pady=2)
        
        self.a_entry = ttk.Entry(self)
        self.a_entry.insert(0, answer)
        self.a_entry.grid(row=1, column=1, sticky=EW, padx=5, pady=2)
        
        # Deck Selection
        self.deck_var = ttk.StringVar(value=assigned_deck)
        # Use a local copy to avoid polluting the global available_decks list with generated names
        deck_options = list(available_decks)
        if assigned_deck and assigned_deck not in deck_options:
            deck_options.append(assigned_deck)
            
        self.deck_dropdown = ttk.Combobox(self, textvariable=self.deck_var, values=deck_options, width=20, state="readonly")
        self.deck_dropdown.grid(row=0, column=2, rowspan=2, padx=10)
        self.deck_dropdown.bind('<Button-1>', lambda e: self.deck_dropdown.event_generate('<Down>'))

        # Source Quote Button - Always visible to keep layout consistent
        btn_state = "normal" if self.quote else "disabled"
        btn_style = "info-outline" if self.quote else "secondary-outline"
        
        self.quote_btn = ttk.Button(self, text="❝", command=self.show_source, bootstyle=btn_style, width=3, state=btn_state)
        self.quote_btn.grid(row=0, column=3, rowspan=2, padx=2)
        
        if self.quote:
            ToolTip(self.quote_btn, text=f"Source: {self.quote[:100]}...")

        # Remove Button
        self.remove_btn = ttk.Button(self, text="🗑", command=self.remove_row, bootstyle="danger-outline", width=3)
        self.remove_btn.grid(row=0, column=4, rowspan=2, padx=5)

    def get_data(self):
        return {
            "question": self.q_entry.get(),
            "answer": self.a_entry.get(),
            "deck": self.deck_var.get(),
            "approved": self.approved_var.get()
        }

    def show_source(self):
        messagebox.showinfo("Source Context", self.quote)

    def remove_row(self):
        if self.on_remove:
            self.on_remove(self)

class AnkiGeneratorUI(ttk.Window):
    def __init__(self):
        self.load_config()
        theme = self.config.get("theme", "darkly")
        super().__init__(themename=theme)
        
        self.title(f"AI Anki Card Generator")
        self.geometry("1200x800")
        
        # Data
        self.selected_file_path = None
        self.available_decks = []
        self.deck_vars = {}
        self.deck_checkboxes = []
        self.card_rows = []
        self.source_text = ""
        self.stop_requested = False
        
        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True)
        
        self.main_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.main_tab, text="Generator")
        self.notebook.add(self.settings_tab, text="Settings")
        
        self.setup_main_tab()
        self.setup_settings_tab()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initial Fetch
        self.fetch_decks()

    def setup_main_tab(self):
        self.main_tab.columnconfigure(0, weight=1)
        self.main_tab.rowconfigure(0, weight=1) # Review area expands (now at top)
        
        # 1. Review Area (Scrollable) - Moved to Top
        self.review_container = ttk.Labelframe(self.main_tab, text="Review & Source Comparison")
        self.review_container.grid(row=0, column=0, sticky=NSEW, padx=20, pady=(20, 10))
        
        # Review Toolbar (Select All / None)
        toolbar = ttk.Frame(self.review_container)
        toolbar.pack(fill=X, padx=5, pady=2)
        
        ttk.Button(toolbar, text="Check All", command=lambda: self.toggle_all_approvals(True), 
                   bootstyle="secondary-outline", width=10).pack(side=LEFT, padx=2)
        ttk.Button(toolbar, text="Uncheck All", command=lambda: self.toggle_all_approvals(False), 
                   bootstyle="secondary-outline", width=12).pack(side=LEFT, padx=2)

        # Proposal: Clear All Button
        ttk.Button(toolbar, text="Clear All", command=self.clear_all_cards, bootstyle="danger-link").pack(side=RIGHT, padx=5)

        # Review Area (Single Pane)
        self.review_frame = ScrolledFrame(self.review_container, autohide=True)
        self.review_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # 2. Input & Decks - Moved to Middle
        top_frame = ttk.Frame(self.main_tab)
        top_frame.grid(row=1, column=0, sticky=EW, padx=20, pady=10)
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # Left Panel (Input Configuration)
        left_panel = ttk.Labelframe(top_frame, text="Input Configuration", padding=15)
        left_panel.grid(row=0, column=0, sticky=NSEW, padx=(0, 10))
        left_panel.columnconfigure(0, weight=1)

        # File Info Box
        self.file_box = ttk.Frame(left_panel, padding=10, relief=RIDGE, borderwidth=1)
        self.file_box.pack(fill=X, pady=(0, 10))
        
        self.emoji_label = ttk.Label(self.file_box, text="📎", font=("Segoe UI Emoji", 24), anchor="center")
        self.emoji_label.pack(side=LEFT, padx=10)

        self.file_label = ttk.Label(self.file_box, text="No file selected", font=("Helvetica", 10), anchor="w")
        self.file_label.pack(side=LEFT, fill=X, expand=True)
        
        # Select PDF Button
        self.select_btn = ttk.Button(left_panel, text="Select PDF", command=self.select_file, bootstyle="primary-outline")
        self.select_btn.pack(fill=X, pady=(0, 10))

        # Language Selection
        lang_frame = ttk.Frame(left_panel)
        lang_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(lang_frame, text="Card Language:").pack(side=LEFT)
        
        langs = ["English", "Turkish", "Spanish", "French", "German", "Japanese", "Chinese"]
        self.lang_var = ttk.StringVar(value=self.config.get("language", "English"))
        self.lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, values=langs, state="readonly")
        self.lang_combo.pack(side=RIGHT, fill=X, expand=True, padx=(10, 0))
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        # Generate Button
        self.generate_btn = ttk.Button(left_panel, text="Generate Cards", command=self.start_processing, bootstyle="success")
        self.generate_btn.pack(fill=X)

        # Right Panel (Deck List)
        deck_frame = ttk.Labelframe(top_frame, text="Available Decks", padding=5)
        deck_frame.grid(row=0, column=1, sticky=NSEW)
        
        self.deck_list_frame = ScrolledFrame(deck_frame, autohide=True)
        self.deck_list_frame.pack(fill=BOTH, expand=True)

        # 3. Bottom Bar: Logs & Sync
        bottom_frame = ttk.Frame(self.main_tab)
        bottom_frame.grid(row=2, column=0, sticky=EW, padx=20, pady=20)
        
        self.log_area = ScrolledText(bottom_frame, height=6, state='disabled', font=("Segoe UI", 9))
        self.log_area.pack(side=LEFT, padx=10, fill=X, expand=True)
        
        # Right side buttons container
        btns_frame = ttk.Frame(bottom_frame)
        btns_frame.pack(side=RIGHT, padx=10, pady=10)

        self.stop_btn = ttk.Button(btns_frame, text="Stop Processing", command=self.stop_processing, bootstyle="danger", state="disabled")
        self.stop_btn.pack(side=TOP, fill=X, pady=(0, 5))

        self.sync_btn = ttk.Button(btns_frame, text="Sync Approved to Anki", command=self.sync_to_anki, state="disabled")
        self.sync_btn.pack(side=TOP, fill=X)

    def setup_settings_tab(self):
        # Use ScrolledFrame to ensure settings are accessible on smaller screens
        scroll_wrapper = ScrolledFrame(self.settings_tab, autohide=True)
        scroll_wrapper.pack(fill=BOTH, expand=True)
        
        container = ttk.Frame(scroll_wrapper, padding=20)
        container.pack(fill=BOTH, expand=True)
        
        # Theme Settings
        theme_frame = ttk.Labelframe(container, text="Appearance", padding=15)
        theme_frame.pack(fill=X, pady=10)
        
        ttk.Label(theme_frame, text="Theme:").pack(side=LEFT, padx=5)
        current_theme = self.config.get("theme", "darkly")
        self.theme_var = ttk.StringVar(value=current_theme)
        themes = ["cyborg", "solar", "darkly", "flatly", "cerulean", "superhero", "journal", "morph"]
        theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=themes, state="readonly")
        theme_combo.pack(side=LEFT, padx=5)
        theme_combo.bind("<<ComboboxSelected>>", self.apply_theme)
        
        # AI Settings
        ai_frame = ttk.Labelframe(container, text="AI Server Configuration (OpenAI Compatible / Local LLM)", padding=15)
        ai_frame.pack(fill=X, pady=10)
        
        ai_grid = ttk.Frame(ai_frame)
        ai_grid.pack(fill=X)
        
        # URL
        ttk.Label(ai_grid, text="API URL:").grid(row=0, column=0, sticky=W, pady=5)
        self.api_url_var = ttk.StringVar(value=self.config.get("api_url", "http://localhost:1234/v1/chat/completions"))
        ttk.Entry(ai_grid, textvariable=self.api_url_var, width=50).grid(row=0, column=1, sticky=EW, padx=10, pady=5)
        ttk.Label(ai_grid, text="(e.g. http://localhost:1234/v1/chat/completions)").grid(row=0, column=2, sticky=W, padx=5)
        
        # Key
        ttk.Label(ai_grid, text="API Key:").grid(row=1, column=0, sticky=W, pady=5)
        self.api_key_var = ttk.StringVar(value=self.config.get("api_key", "lm-studio"))
        ttk.Entry(ai_grid, textvariable=self.api_key_var, width=50).grid(row=1, column=1, sticky=EW, padx=10, pady=5)
        
        # Model Parameters
        param_frame = ttk.Labelframe(container, text="Model Parameters", padding=15)
        param_frame.pack(fill=X, pady=10)
        
        # Model Name
        ttk.Label(param_frame, text="Model Name:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.model_var = ttk.StringVar(value=self.config.get("model", "local-model"))
        ttk.Entry(param_frame, textvariable=self.model_var, width=30).grid(row=0, column=1, sticky=W, padx=5)
        
        # Temperature
        ttk.Label(param_frame, text="Temperature (0.0 - 1.0):").grid(row=0, column=2, sticky=W, padx=15, pady=5)
        self.temp_var = ttk.DoubleVar(value=self.config.get("temperature", 0.7))
        ttk.Spinbox(param_frame, textvariable=self.temp_var, from_=0.0, to=1.0, increment=0.1, width=10).grid(row=0, column=3, sticky=W, padx=5)
        
        # Max Tokens
        ttk.Label(param_frame, text="Max Tokens (-1 for auto):").grid(row=0, column=4, sticky=W, padx=15, pady=5)
        self.tokens_var = ttk.IntVar(value=self.config.get("max_tokens", -1))
        ttk.Entry(param_frame, textvariable=self.tokens_var, width=10).grid(row=0, column=5, sticky=W, padx=5)
        
        # Context Window
        ttk.Label(param_frame, text="Context Window:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.ctx_var = ttk.IntVar(value=self.config.get("context_window", 4096))
        ttk.Entry(param_frame, textvariable=self.ctx_var, width=30).grid(row=1, column=1, sticky=W, padx=5)

        # Concurrency
        ttk.Label(param_frame, text="Concurrency:").grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.concurrency_var = ttk.IntVar(value=self.config.get("concurrency", 1))
        ttk.Spinbox(param_frame, textvariable=self.concurrency_var, from_=1, to=10, width=5).grid(row=2, column=1, sticky=W, padx=5)

        # Card Density
        ttk.Label(param_frame, text="Card Density:").grid(row=1, column=2, sticky=W, padx=15, pady=5)
        self.density_var = ttk.StringVar(value=self.config.get("card_density", "Medium"))
        density_combo = ttk.Combobox(param_frame, textvariable=self.density_var, values=["Low", "Medium", "High"], state="readonly", width=10)
        density_combo.grid(row=1, column=3, sticky=W, padx=5)

        # Quality Control
        qc_frame = ttk.Labelframe(container, text="Quality Control & Filters", padding=15)
        qc_frame.pack(fill=X, pady=10)
        
        self.filter_yes_no_var = ttk.BooleanVar(value=self.config.get("filter_yes_no", True))
        ttk.Checkbutton(qc_frame, text="Auto-remove 'Yes/No' questions", variable=self.filter_yes_no_var, bootstyle="round-toggle").pack(anchor=W, pady=2)
        
        self.exclude_trivia_var = ttk.BooleanVar(value=self.config.get("exclude_trivia", True))
        ttk.Checkbutton(qc_frame, text="Exclude biographical trivia (dates, names)", variable=self.exclude_trivia_var, bootstyle="round-toggle").pack(anchor=W, pady=2)
        
        self.smart_deck_match_var = ttk.BooleanVar(value=self.config.get("smart_deck_match", True))
        ttk.Checkbutton(qc_frame, text="Smart Deck Matching (Content analysis + Shuffle)", variable=self.smart_deck_match_var, bootstyle="round-toggle").pack(anchor=W, pady=2)
        
        self.ai_refinement_var = ttk.BooleanVar(value=self.config.get("ai_refinement", False))
        ttk.Checkbutton(qc_frame, text="AI Refinement (Two-Pass: Generation -> AI Check -> Edit)", variable=self.ai_refinement_var, bootstyle="round-toggle").pack(anchor=W, pady=2)

        # Prompt Settings
        prompt_frame = ttk.Labelframe(container, text="Custom Prompt / Style Instructions", padding=15)
        prompt_frame.pack(fill=BOTH, expand=True, pady=10)
        
        ttk.Label(prompt_frame, text="Add custom instructions (e.g., 'Make questions difficult', 'Focus on dates'):").pack(anchor=W, pady=(0, 5))
        
        self.prompt_text = ScrolledText(prompt_frame, height=4, font=("Segoe UI", 10))
        self.prompt_text.pack(fill=BOTH, expand=True)
        self.prompt_text.insert("1.0", self.config.get("prompt_style", ""))

        # Save Button
        ttk.Button(container, text="Save Settings", command=self.save_settings_ui, bootstyle="primary").pack(pady=20, anchor=E)

    def load_config(self):
        self.config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                pass
    
    def save_settings_ui(self):
        self.config["theme"] = self.theme_var.get()
        self.config["language"] = self.lang_var.get()
        self.config["api_url"] = self.api_url_var.get()
        self.config["api_key"] = self.api_key_var.get()
        self.config["model"] = self.model_var.get()
        self.config["temperature"] = self.temp_var.get()
        self.config["max_tokens"] = self.tokens_var.get()
        self.config["context_window"] = self.ctx_var.get()
        self.config["concurrency"] = self.concurrency_var.get()
        self.config["card_density"] = self.density_var.get()
        self.config["filter_yes_no"] = self.filter_yes_no_var.get()
        self.config["exclude_trivia"] = self.exclude_trivia_var.get()
        self.config["smart_deck_match"] = self.smart_deck_match_var.get()
        self.config["ai_refinement"] = self.ai_refinement_var.get()
        self.config["prompt_style"] = self.prompt_text.get("1.0", "end-1c")
        self.save_config()
        messagebox.showinfo("Settings", "Settings saved successfully.")

    def save_config(self):
        # Update config object from vars if they exist (for auto-saves like language)
        if hasattr(self, 'lang_var'): self.config["language"] = self.lang_var.get()
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def apply_theme(self, event):
        t = self.theme_var.get()
        self.style.theme_use(t)

    def fetch_decks(self):
        self.log("Connecting to Anki...")
        threading.Thread(target=self._fetch_decks_thread).start()

    def _fetch_decks_thread(self):
        decks = get_deck_names(log_callback=self.log)
        if decks:
            self.available_decks = decks
            self.log(f"Connected to Anki. Found {len(decks)} decks.")
        else:
            self.available_decks = ["Default"]
            self.log("Could not connect to Anki Add-on. Is Anki open?")
        
        self.after(0, self.update_deck_list_ui)

    def update_deck_list_ui(self):
        # Clear previous checkboxes
        for cb in self.deck_checkboxes:
            cb.destroy()
        self.deck_checkboxes = []
        self.deck_vars = {}
        
        saved_decks = self.config.get("selected_decks", [])
        is_first_run = "selected_decks" not in self.config

        if self.available_decks:
            for deck in sorted(self.available_decks):
                var = ttk.BooleanVar()
                # Default to selected if it's the first run, otherwise check config
                if is_first_run:
                    var.set(True)
                else:
                    var.set(deck in saved_decks)
                
                self.deck_vars[deck] = var
                cb = ttk.Checkbutton(self.deck_list_frame, text=deck, variable=var, command=self.save_deck_selection)
                cb.pack(anchor=W, padx=5, pady=2, fill=X)
                self.deck_checkboxes.append(cb)
        else:
            lbl = ttk.Label(self.deck_list_frame, text="(No decks found)")
            lbl.pack(anchor=W, padx=5)
            self.deck_checkboxes.append(lbl)

    def save_deck_selection(self):
        selected = [d for d, v in self.deck_vars.items() if v.get()]
        self.config["selected_decks"] = selected
        self.save_config()

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            
            # Uzun dosya isimlerini kısalt (UI bozulmasını önlemek için)
            if len(filename) > 35:
                display_text = filename[:32] + "..."
            else:
                display_text = filename
            
            self.file_label.config(text=display_text)
            self.emoji_label.config(text="📄")
            ToolTip(self.file_label, text=filename)

    def log(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert("end", message + "\n")
        # Limit to approx 50000 characters
        text = self.log_area.get("1.0", "end")
        if len(text) > 50000:
            excess = len(text) - 50000
            self.log_area.delete("1.0", f"1.0+{excess}c")
        self.log_area.see("end")
        self.log_area.config(state='disabled')

    def start_processing(self):
        if not self.selected_file_path:
            messagebox.showwarning("Warning", "Please select a PDF file first.")
            return
        
        # Ensure we capture the latest prompt from the UI even if "Save Settings" wasn't clicked
        if hasattr(self, 'prompt_text'):
            self.config["prompt_style"] = self.prompt_text.get("1.0", "end-1c")

        target_lang = self.lang_var.get()
        api_url = self.api_url_var.get()
        api_key = self.api_key_var.get()
        model = self.model_var.get()
        temperature = self.temp_var.get()
        max_tokens = self.tokens_var.get()
        context_window = self.config.get("context_window", 4096)
        concurrency = self.config.get("concurrency", 1)
        card_density = self.density_var.get()
        prompt_style = self.config.get("prompt_style", "")
        filter_yes_no = self.filter_yes_no_var.get()
        exclude_trivia = self.exclude_trivia_var.get()
        smart_deck_match = self.smart_deck_match_var.get()
        ai_refinement = self.ai_refinement_var.get()
        
        # Get selected decks
        selected_decks = [d for d, v in self.deck_vars.items() if v.get()]
        
        # If no specific decks are selected, let AI choose from ALL available decks
        if not selected_decks:
            self.log("No specific decks selected. AI will choose from all available decks.")
            selected_decks = self.available_decks
        
        self.generate_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_requested = False
        self.log("Starting processing...")
        
        threading.Thread(target=self.run_process, args=(self.selected_file_path, target_lang, api_url, api_key, model, temperature, max_tokens, prompt_style, selected_decks, context_window, concurrency, card_density, filter_yes_no, exclude_trivia, smart_deck_match, ai_refinement), daemon=True).start()

    def run_process(self, file_path, target_lang, api_url, api_key, model, temperature, max_tokens, prompt_style, deck_names, context_window, concurrency, card_density, filter_yes_no, exclude_trivia, smart_deck_match, ai_refinement):
        try:
            self.log(f"Extracting text from {os.path.basename(file_path)}...")
            text = extract_text_from_pdf(file_path)
            
            if not text or not text.strip():
                self.log("Error: No text extracted from PDF. It might be image-based, encrypted, or corrupted.")
                self.after(0, lambda: self.generate_btn.config(state="normal"))
                return

            self.log(f"Extracted {len(text)} characters.")
            
            self.source_text = text
            
            self.log("Generating Q&A with LLM...")
            
            # Clear existing cards before starting
            self.after(0, self.clear_review_area)
            
            # Define callback to add cards as they arrive
            def on_chunk_generated(new_cards):
                # Capture list by value (copy) to ensure thread safety
                cards_copy = list(new_cards)
                self.after(0, lambda: self.append_cards_to_review(cards_copy))

            # Pass available decks so LLM can categorize
            qa_data = generate_qa_pairs(text, deck_names=deck_names, target_language=target_lang, log_callback=self.log, api_url=api_url, api_key=api_key, model=model, temperature=temperature, max_tokens=max_tokens, prompt_style=prompt_style, context_window=context_window, concurrency=concurrency, card_density=card_density, partial_result_callback=on_chunk_generated, stop_callback=lambda: self.stop_requested, filter_yes_no=filter_yes_no, exclude_trivia=exclude_trivia, smart_deck_match=smart_deck_match, ai_refinement=ai_refinement)
            
            # Final log
            self.after(0, lambda: self.log(f"Generation complete. Total {len(qa_data)} cards. Please review and approve."))

        except Exception as e:
            self.log(f"Error: {str(e)}")
        finally:
            self.after(0, lambda: self.generate_btn.config(state="normal"))
            self.after(0, lambda: self.stop_btn.config(state="disabled"))

    def clear_review_area(self):
        for row in self.card_rows:
            row.destroy()
        self.card_rows = []

    def append_cards_to_review(self, new_cards):
        self.log(f"UI: Appending {len(new_cards)} new cards...")
        for item in new_cards:
            row = CardReviewRow(
                self.review_frame, 
                item['question'], 
                item['answer'], 
                item['deck'], 
                self.available_decks,
                quote=item.get('quote', ''),
                on_remove=self.remove_card_row
            )
            self.card_rows.append(row)
        
        # Force layout update to ensure new cards are visible
        self.review_frame.update_idletasks()
        
        # Enable sync button immediately if we have cards
        if self.card_rows:
            self.sync_btn.config(state="normal")

    def remove_card_row(self, row):
        if row in self.card_rows:
            self.card_rows.remove(row)
            row.destroy()

    def stop_processing(self):
        if messagebox.askyesno("Stop", "Are you sure you want to stop processing?"):
            self.stop_requested = True
            self.log("Stopping processing...")
            self.stop_btn.config(state="disabled")

    def on_close(self):
        """Handle window closing event to ensure all threads are killed."""
        self.stop_requested = True
        self.destroy()
        os._exit(0)

    def clear_all_cards(self):
        if self.card_rows and messagebox.askyesno("Confirm", "Clear all generated cards?"):
            for row in self.card_rows:
                row.destroy()
            self.card_rows = []
            
    def toggle_all_approvals(self, state):
        for row in self.card_rows:
            row.approved_var.set(state)

    def sync_to_anki(self):
        approved_cards = []
        for row in self.card_rows:
            data = row.get_data()
            if data['approved']:
                approved_cards.append(data)
        
        if not approved_cards:
            messagebox.showinfo("Info", "No cards approved.")
            return

        # Group by deck to send efficiently (or just send one by one, but grouping is cleaner)
        # Our current anki_integration takes (deck_name, list_of_pairs)
        # So we group them.
        deck_groups = {}
        for card in approved_cards:
            d_name = card['deck']
            if d_name not in deck_groups:
                deck_groups[d_name] = []
            deck_groups[d_name].append((card['question'], card['answer']))
        
        total_added = 0
        try:
            for deck_name, pairs in deck_groups.items():
                count = create_anki_deck(deck_name, pairs, log_callback=self.log)
                total_added += count
            
            messagebox.showinfo("Success", f"Successfully added {total_added} cards to Anki!")
            self.log(f"Synced {total_added} cards.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
