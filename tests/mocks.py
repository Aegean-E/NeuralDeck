import json

class MockLLM:
    def __init__(self, response_map=None):
        self.response_map = response_map or {}
        self.default_response = '[{"question": "Mock Q", "answer": "Mock A", "deck": "Default"}]'

    def call(self, prompt, system_instruction, **kwargs):
        # Determine response based on prompt content
        for key, resp in self.response_map.items():
            if key in prompt:
                return resp
        return self.default_response

class MockAnki:
    def __init__(self):
        self.decks = {}

    def add_cards(self, deck_name, cards):
        if deck_name not in self.decks:
            self.decks[deck_name] = []
        self.decks[deck_name].extend(cards)
        return len(cards)

    def get_decks(self):
        return list(self.decks.keys())
