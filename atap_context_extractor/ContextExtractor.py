import logging
import traceback
from logging.handlers import RotatingFileHandler
from os.path import abspath, join, dirname
from typing import Optional

import panel as pn
from atap_corpus._types import TCorpora
from atap_corpus.corpus.corpus import DataFrameCorpus
from atap_corpus_loader import CorpusLoader
from pandas import DataFrame
from panel import Row, Column
from panel.widgets import Tqdm, Button, TextInput, Select, IntInput, Checkbox

from atap_context_extractor.extractor import Extractor, SearchTerm, ContextType

pn.extension()


class ContextExtractor(pn.viewable.Viewer):
    """
    A tool for extracting the context around searched text in a corpus
    """
    LOGGER_NAME: str = "corpus-extractor"
    CONTEXT_TYPES: list[str] = [context for context in ContextType]

    @staticmethod
    def setup_logger(logger_name: str, run_logger: bool):
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        if not run_logger:
            logger.addHandler(logging.NullHandler())
            return

        formatter = logging.Formatter(
            '%(asctime)s %(levelname)6s - %(name)s:%(lineno)4d %(funcName)20s() - %(message)s')
        log_file_location = abspath(join(dirname(__file__), '..', 'log.txt'))
        # Max size is ~10MB with 1 backup, so a max size of ~20MB for log files
        max_bytes: int = 10000000
        backup_count: int = 1
        file_handler = RotatingFileHandler(log_file_location, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        logger.info('Logger started')

    @staticmethod
    def log(msg: str, level: int):
        logger = logging.getLogger(ContextExtractor.LOGGER_NAME)
        logger.log(level, msg)

    def __init__(self,
                 corpus_loader: Optional[CorpusLoader] = None,
                 run_logger: bool = False,
                 **params):
        """
        ContextExtractor constructor
        :param corpus_loader: The CorpusLoader that the extractor will be attached to. If None, a default CorpusLoader will be created with no optional features. None by Default.
        :type corpus_loader: Optional[CorpusLoader]
        :param run_logger: If True, a log file will be written to. False by default.
        :type run_logger: bool
        """
        super().__init__(**params)

        ContextExtractor.setup_logger(ContextExtractor.LOGGER_NAME, run_logger)

        self.search_terms: list[SearchTerm] = []

        self.progress_bar = Tqdm(visible=False)
        self.corpus_selector = Select(name='Selected corpus')

        self.search_term_input = TextInput(name='Search term')
        self.ignore_case = Checkbox(name="Ignore case")
        self.use_regex = Checkbox(name="Regular expression")
        self.whole_words = Checkbox(name="Whole words", value=True)
        self.add_search_term_button = Button(
            name="Add search term",
            button_type="primary", button_style="solid",
            align='center'
        )
        self.add_search_term_button.on_click(self._add_search_term)

        self.context_count_input = IntInput(name='Context count', value=100, start=0)
        self.context_type = Select(name='Context type', options=ContextExtractor.CONTEXT_TYPES)

        self.extract_corpus_button = Button(
            name="Extract",
            button_type="success", button_style="solid",
            align='end'
        )
        self.extract_corpus_button.on_click(self.extract_corpus)

        self.name_field = TextInput(name='Name', placeholder='Enter a name (leave blank to autogenerate)')

        self.extractor_panel = pn.Column(height=500, visible=False)
        self._update_display()

        if corpus_loader:
            self.corpus_loader: CorpusLoader = corpus_loader
        else:
            self.corpus_loader: CorpusLoader = CorpusLoader(root_directory='.', run_logger=run_logger)
        self.corpora: TCorpora = self.corpus_loader.get_mutable_corpora()

        self.corpus_loader.register_event_callback("build", self._on_corpora_update)
        self.corpus_loader.register_event_callback("rename", self._on_corpora_update)
        self.corpus_loader.register_event_callback("delete", self._on_corpora_update)
        self.corpus_loader.add_tab("Context Extractor", self.extractor_panel)
        self._on_corpora_update()

    def __panel__(self):
        return self.corpus_loader.servable()

    def get_corpus_loader(self) -> CorpusLoader:
        return self.corpus_loader

    def get_mutable_corpora(self) -> TCorpora:
        return self.corpora

    def display_error(self, error_msg: str):
        self.log(f"Error displayed: {error_msg}", logging.DEBUG)
        pn.state.notifications.error(error_msg, duration=0)

    def display_success(self, success_msg: str):
        self.log(f"Success displayed: {success_msg}", logging.DEBUG)
        pn.state.notifications.success(success_msg, duration=3000)

    def _update_display(self, *_):
        remove_buttons = []
        for search_term in self.search_terms:
            label = f'{str(search_term)} \U00002A09'
            remove_button = Button(name=label, button_style="outline")
            remove_button.on_click(lambda *_, term=search_term: self._remove_search_term(term))
            remove_buttons.append(remove_button)

        panel_objects = [
            self.corpus_selector,
            Row(self.search_term_input, Column(self.ignore_case, self.use_regex, self.whole_words), self.add_search_term_button),
            Row(*remove_buttons),
            self.progress_bar,
            Row(self.context_count_input, self.context_type),
            Row(self.extract_corpus_button, self.name_field)
        ]
        self.extractor_panel.objects = panel_objects

    def _on_corpora_update(self, corpus=None, *_):
        if self.corpus_loader is None:
            self.extractor_panel.visible = False

        formatted_dict: dict[str, DataFrameCorpus] = {}
        for corpus in self.corpora.items():
            label = f"{corpus.name} | docs: {len(corpus)}"
            if corpus.parent:
                label += f" | parent: {corpus.parent.name}"
            formatted_dict[label] = corpus
        self.corpus_selector.options = formatted_dict

        corpus_exists = bool(len(formatted_dict))
        if corpus_exists:
            self.corpus_selector.value = list(formatted_dict.values())[-1]
        else:
            self.corpus_selector.value = None

        self.extractor_panel.visible = corpus_exists
        self._update_display()

    def _set_components_state(self, enabled: bool):
        self.corpus_selector.disabled = not enabled
        self.search_term_input.disabled = not enabled
        self.ignore_case.disabled = not enabled
        self.use_regex.disabled = not enabled
        self.add_search_term_button.disabled = not enabled
        self.context_count_input.disabled = not enabled
        self.context_type.disabled = not enabled
        self.extract_corpus_button.disabled = not enabled
        self.name_field.disabled = not enabled

    def _add_search_term(self, *_):
        text: str = self.search_term_input.value_input
        if len(text) == 0:
            self.display_error("Search term must contain at least one character")
            return

        use_regex: bool = self.use_regex.value
        ignore_case: bool = self.ignore_case.value
        whole_words: bool = self.whole_words.value

        search_term = SearchTerm(text, use_regex, ignore_case, whole_words)
        self.search_terms.append(search_term)

        self.use_regex.value = False
        self.ignore_case.value = False
        self.whole_words.value = True
        self.search_term_input.value = ""
        self.search_term_input.value_input = ""

        self.log(f"SearchTerm added: {search_term.__repr__()}", logging.DEBUG)
        self._update_display()

    def _remove_search_term(self, search_term: SearchTerm):
        self.log(f"SearchTerm removed: {search_term.__repr__()}", logging.DEBUG)
        self.search_terms.remove(search_term)
        self._update_display()

    def extract_corpus(self, *_):
        self.log("extract_corpus method called", logging.DEBUG)
        if (self.corpus_loader is None) or (self.corpus_selector.value is None):
            self.display_error("No corpus selected")
            return

        if len(self.search_terms) == 0:
            self.display_error("No search terms added. Click 'Add search term' to add a search term")
            return

        orig_corpus: DataFrameCorpus = self.corpus_selector.value
        if len(orig_corpus) == 0:
            self.display_error("Selected corpus contains no documents")
            return

        col_doc: str = orig_corpus._COL_DOC
        corpus_df: DataFrame = orig_corpus.to_dataframe()

        new_name = self.name_field.value_input
        i = 0
        while (not len(new_name)) or (self.corpora.get(new_name) is not None):
            # Selects an extracted corpus name that is not empty and doesn't conflict with existing names
            new_name = f"{orig_corpus.name}_extracted.{i}"
            i += 1

        context_type: ContextType = ContextType(self.context_type.value)
        context_count: int = self.context_count_input.value

        self.progress_bar.visible = True
        self._set_components_state(False)
        try:
            self.log("extract_corpus: starting corpus extraction", logging.DEBUG)
            extracted_df: DataFrame = Extractor.extract_context_df(corpus_df, col_doc,
                                                                   self.search_terms, context_type,
                                                                   context_count, self.progress_bar)
            self.log("extract_corpus: building new corpus from dataframe", logging.DEBUG)
            extracted_corpus: DataFrameCorpus = DataFrameCorpus.from_dataframe(extracted_df, col_doc=col_doc, name=new_name)
            self.log("extract_corpus: Adding corpus to corpora", logging.DEBUG)
            self.corpora.add(extracted_corpus)
        except Exception as e:
            self.log(traceback.format_exc(), logging.DEBUG)
            self.display_error(f"Error extracting context: {str(e)}")
            self.progress_bar.visible = False
            self._set_components_state(True)
            return

        self.progress_bar.visible = False
        self._set_components_state(True)
        self.search_terms = []
        self._on_corpora_update()

        self.display_success(f"Context extracted successfully. Extracted corpus: {extracted_corpus.name}")
