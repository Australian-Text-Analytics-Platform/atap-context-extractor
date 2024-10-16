from typing import Callable, Hashable

from pandas import DataFrame, concat
from panel.widgets import Tqdm
from regex import regex, Pattern, Match

from atap_context_extractor.extractor.ContextType import ContextType
from atap_context_extractor.extractor.SearchTerm import SearchTerm


class Extractor:
    @staticmethod
    def split_by_character(to_split: str) -> list[str]:
        return list(to_split)

    @staticmethod
    def split_by_word(to_split: str) -> list[str]:
        return regex.findall(r'\s*\S+\s*', to_split)

    @staticmethod
    def split_by_line(to_split: str) -> list[str]:
        return regex.findall(r'.*?(?:\n|$)', to_split)

    CONTEXT_TYPE_MAP: dict[str, Callable] = {
        ContextType.CHARACTERS: split_by_character,
        ContextType.WORDS: split_by_word,
        ContextType.LINES: split_by_line,
    }

    @staticmethod
    def extract_context_df(df: DataFrame, doc_col: str, search_terms: list[SearchTerm],
                           context_type: ContextType, context_count: int, tqdm_obj: Tqdm) -> DataFrame:
        split_fn: Callable = Extractor.CONTEXT_TYPE_MAP[context_type]
        search_patterns: list[Pattern] = []
        for term in search_terms:
            flags = regex.DOTALL
            if term.ignore_case:
                flags = flags | regex.I
            term_text = term.text
            if not term.use_regex:
                term_text = regex.escape(term_text)
            term_pattern = regex.compile(term_text, flags=flags)
            search_patterns.append(term_pattern)

        match_col: str = "match"
        while match_col in df.columns:
            match_col += '_'
        match_idx_col: str = "match_idx"
        while match_idx_col in df.columns:
            match_idx_col += '_'
        context_idx_col: str = "context_idx"
        while context_idx_col in df.columns:
            context_idx_col += '_'

        dict_df = df.to_dict(orient="records")

        def _extract_row_generator():
            for idx, row_dict in tqdm_obj(enumerate(dict_df), total=df.shape[0], desc="Extracting context", unit='documents'):
                yield Extractor.extract_context_row(row_dict, idx, doc_col, match_col, match_idx_col, context_idx_col, split_fn, context_count, search_patterns)

        return concat(_extract_row_generator(), ignore_index=True)

    @staticmethod
    def get_formatted_index(start: int, end: int) -> str:
        return f"({start},{end})"

    @staticmethod
    def extract_context_row(row_dict: dict, row_idx: Hashable, doc_col: str, match_col: str,
                            match_idx_col: str, context_idx_col: str,
                            split_fn: Callable, context_count: int,
                            search_patterns: list[Pattern]) -> DataFrame:
        row_idx_col: str = 'source_doc'
        new_data_cols: list[str] = list(row_dict.keys()) + [row_idx_col, match_col, match_idx_col, context_idx_col]
        new_data: dict[str, list] = {k: [] for k in new_data_cols}

        text = str(row_dict[doc_col])
        match: Match
        for pattern in search_patterns:
            for match in regex.finditer(pattern, text, overlapped=True):
                row_data = row_dict.copy()

                match_start, match_end = match.span()
                match: str = match.group()
                row_data[match_col] = match
                row_data[row_idx_col] = row_idx

                left_context: str = ''
                right_context: str = ''
                if context_count > 0:
                    left_context_split = split_fn(text[:match_start])
                    right_context_split = split_fn(text[match_end:])
                    left_context = ''.join(left_context_split[-context_count:])
                    right_context = ''.join(right_context_split[:context_count])
                row_data[doc_col] = left_context + match + right_context

                context_idx_start = match_start - len(left_context)
                context_idx_end = match_end + len(right_context)

                row_data[match_idx_col] = Extractor.get_formatted_index(match_start, match_end)
                row_data[context_idx_col] = Extractor.get_formatted_index(context_idx_start, context_idx_end)

                for key, value in row_data.items():
                    new_data[key].append(value)

        return DataFrame(new_data)
