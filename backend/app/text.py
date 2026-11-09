"""Small text helpers shared by repositories."""
import unicodedata


def normalize_search(text: str) -> str:
    """Lowercase, strip accents and collapse whitespace ('  Nikola JOKIĆ ' -> 'nikola jokic').

    Must match how src/export_db.py builds players.search_name.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def escape_like(text: str) -> str:
    """Escape LIKE wildcards in user input (use with ESCAPE '\\')."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
