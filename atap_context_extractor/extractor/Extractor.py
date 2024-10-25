from typing import Callable

from pandas import DataFrame, Series
from panel.widgets import Tqdm
from regex import regex, Pattern, Match

from atap_context_extractor.extractor.ContextType import ContextType
from atap_context_extractor.extractor.SearchTerm import SearchTerm


class Extractor:
    WORD_PATTERN: Pattern = regex.compile(r'\s*\S+\s*')
    LINE_PATTERN: Pattern = regex.compile(r'.*?(?:\n|$)')

    @staticmethod
    def split_by_character(to_split: str) -> list[str]:
        return list(to_split)

    @staticmethod
    def split_by_word(to_split: str) -> list[str]:
        return regex.findall(Extractor.WORD_PATTERN, to_split)

    @staticmethod
    def split_by_line(to_split: str) -> list[str]:
        return regex.findall(Extractor.LINE_PATTERN, to_split)

    CONTEXT_TYPE_MAP: dict[ContextType, Callable] = {
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
            if term.whole_words:
                term_text = rf"\b{term_text}\b"
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
        row_idx_col: str = 'source_doc'

        dict_df: list[dict] = df.to_dict(orient='records')

        with tqdm_obj(total=df.shape[0], desc="Extracting context", unit="documents") as progress_bar:
            args = (doc_col, row_idx_col, match_col, match_idx_col, context_idx_col, split_fn, context_count, search_patterns, progress_bar)
            result_dicts = []
            for idx, dict_row in enumerate(dict_df):
                result_dicts.append(Extractor.extract_context_row(dict_row, idx, *args))
        flattened = [item for sublist in result_dicts for item in sublist]

        expected_cols = list(df.columns) + [row_idx_col, match_col, match_idx_col, context_idx_col]
        result_df = DataFrame(flattened, columns=expected_cols)

        return result_df

    @staticmethod
    def get_formatted_index(start: int, end: int) -> str:
        return f"({start},{end})"

    @staticmethod
    def extract_context_row(row: dict, idx: int, doc_col: str, row_idx_col: str, match_col: str,
                            match_idx_col: str, context_idx_col: str,
                            split_fn: Callable, context_count: int,
                            search_patterns: list[Pattern], tqdm_obj) -> list[dict]:
        tqdm_obj.update(1)
        row_idx: int = int(idx)
        new_data: list[dict] = []
        row_dict: dict = row

        text = str(row[doc_col])
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

                new_data.append(row_data)

        return new_data
