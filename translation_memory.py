import json
import os


MEMORY_PATH = os.getenv("TRANSLATION_MEMORY_PATH", "dictionary/translation_memory.json")


def _ensure_parent():
    parent = os.path.dirname(MEMORY_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_memory():
    _ensure_parent()
    if not os.path.exists(MEMORY_PATH):
        return {}

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_memory(memory):
    _ensure_parent()
    with open(MEMORY_PATH, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


def make_key(text, section=None):
    return f"{section or 'UNKNOWN'}::{str(text).strip()}"


def get_memory_translation(text, section=None):
    memory = load_memory()
    return memory.get(make_key(text, section))


def get_memory_translation_from_store(memory, text, section=None):
    if not isinstance(memory, dict):
        return None
    return memory.get(make_key(text, section))


def update_memory_entry(text, translated, section=None):
    source_text = str(text).strip()
    translated_text = str(translated).strip()

    if not source_text or not translated_text:
        return

    memory = load_memory()
    memory[make_key(source_text, section)] = translated_text
    save_memory(memory)


def update_memory_entry_in_store(memory, text, translated, section=None):
    source_text = str(text).strip()
    translated_text = str(translated).strip()

    if not source_text or not translated_text:
        return memory

    if not isinstance(memory, dict):
        memory = {}

    memory[make_key(source_text, section)] = translated_text
    return memory
