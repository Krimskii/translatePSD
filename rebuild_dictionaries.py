from normative_dictionary import DEFAULT_PATH, rebuild_normative_dictionary
from translation_memory import MEMORY_PATH, reset_memory


def rebuild_dictionary_bundle():
    glossary = rebuild_normative_dictionary(DEFAULT_PATH)
    memory = reset_memory(MEMORY_PATH)
    return {
        "normative_workbook": glossary["workbook"],
        "approved_rows": glossary["approved_rows"],
        "candidate_rows": glossary["candidate_rows"],
        "translation_memory_path": memory["path"],
        "translation_memory_entries": memory["entries"],
    }


if __name__ == "__main__":
    summary = rebuild_dictionary_bundle()
    print("Нормативный словарь пересобран:", summary["normative_workbook"])
    print("Утвержденных терминов:", summary["approved_rows"])
    print("Кандидатов:", summary["candidate_rows"])
    print("Память переводов очищена:", summary["translation_memory_path"])
