class SearchTerm:
    def __init__(self, text: str, use_regex: bool = False, ignore_case: bool = False, whole_words: bool = False):
        self.text: str = text
        self.use_regex: bool = use_regex
        self.ignore_case: bool = ignore_case
        self.whole_words: bool = whole_words

    def __str__(self) -> str:
        return self.text

    def __repr__(self):
        return f'Search term: {self.text}, regex: {self.use_regex}, ignore_case: {self.ignore_case}, whole_words: {self.whole_words}'

    def __eq__(self, other) -> bool:
        if not isinstance(other, SearchTerm):
            return False
        return (self.text == other.text) and (self.use_regex == other.use_regex) and (self.ignore_case == other.ignore_case) and (self.whole_words == other.whole_words)

    def __hash__(self):
        return hash(self.text + str(self.use_regex) + str(self.ignore_case) + str(self.whole_words))
