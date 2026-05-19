def chunk_transcript(text: str, max_chars: int = 8_000) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]

