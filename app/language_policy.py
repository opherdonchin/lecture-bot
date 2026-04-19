import re as re_

from langdetect import DetectorFactory, LangDetectException, detect_langs

DetectorFactory.seed = 0

_DISALLOWED_SCRIPT_RE = re_.compile(
    "["
    "\u0400-\u04FF"  # Cyrillic
    "\u0590-\u05FF"  # Hebrew
    "\u0600-\u06FF"  # Arabic
    "\u0900-\u097F"  # Devanagari
    "\u3040-\u30FF"  # Japanese
    "\u3400-\u9FFF"  # CJK
    "\uAC00-\uD7AF"  # Hangul
    "]"
)
_LATIN_TOKEN_RE = re_.compile(r"[A-Za-z']+")
_ENGLISH_HINT_WORDS = {
    "a", "an", "and", "answer", "approximate", "are", "because", "can", "data",
    "difference", "distribution", "draw", "estimate", "example", "explain",
    "for", "from", "give", "how", "if", "in", "is", "it", "likelihood", "model",
    "of", "on", "one", "or", "posterior", "probability", "question", "sample",
    "sampling", "that", "the", "this", "to", "trace", "what", "why", "yes", "no",
}

ENGLISH_ONLY_STUDENT_MESSAGE = (
    "Please write your answer in English. "
    "This tutor only works in English and will not continue with non-English messages."
)
ENGLISH_ONLY_ASSISTANT_FALLBACK = (
    "Please continue in English. This tutor only works in English."
)
ENGLISH_ONLY_REPORT_FALLBACK = (
    "This report is available only in English."
)


def is_english_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if _DISALLOWED_SCRIPT_RE.search(stripped):
        return False

    tokens = _LATIN_TOKEN_RE.findall(stripped)
    alpha_chars = sum(len(token) for token in tokens)
    if alpha_chars == 0:
        return True

    lowered_tokens = [token.lower() for token in tokens]

    # Short ASCII technical noun phrases are often misclassified by language-ID
    # even when they are perfectly fine English tutoring replies.
    if alpha_chars < 40 and stripped.isascii():
        return True

    if alpha_chars < 12:
        if len(lowered_tokens) == 1:
            return True
        if any(token in _ENGLISH_HINT_WORDS for token in lowered_tokens):
            return True

    try:
        detected = detect_langs(stripped)
    except LangDetectException:
        return False
    if not detected:
        return False
    top = detected[0]
    if top.lang == "en" and top.prob >= 0.60:
        return True
    if alpha_chars < 20 and top.lang == "en":
        return True
    return False


def ensure_english_text(text: str, fallback: str) -> str:
    if is_english_text(text):
        return text
    return fallback
