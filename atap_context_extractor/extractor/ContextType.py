from enum import Enum


class ContextType(Enum):
    WORDS = "words"
    CHARACTERS = "characters"
    LINES = "lines"

    def __str__(self):
        return self.value
