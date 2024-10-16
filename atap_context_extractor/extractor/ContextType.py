from enum import Enum


class ContextType(Enum):
    CHARACTERS = "characters"
    WORDS = "words"
    LINES = "lines"

    def __str__(self):
        return self.value
