# atap_context_extractor Documentation

---

## Docs

### atap_context_extractor.ContextExtractor

Public interface for the atap_context_extractor module

Can be imported using:

```python
from atap_context_extractor import ContextExtractor
```

---

### ContextExtractor.\_\_init\_\_

ContextExtractor constructor

Params
- corpus_loader: Optional[CorpusLoader] - The CorpusLoader that the extractor will be attached to. If None, a default CorpusLoader will be created with no optional features. None by Default.
- run_logger: bool - If True, a log file will be written to. False by default.
- params: Any – passed onto the panel.viewable.Viewer super-class

Example

```python
extractor = ContextExtractor(run_logger=True)
```

---

### ContextExtractor.servable

Inherited from panel.viewable.Viewer. Call ContextExtractor.servable() in a Jupyter notebook context to display the ContextExtractor widget.

Example

```python
extractor = ContextExtractor(run_logger=True)
extractor.servable()
```

---

### ContextExtractor.get_corpus_loader

Returns: CorpusLoader - the CorpusLoader object that the ContextExtractor is attached to

Example

```python
extractor = ContextExtractor()
corpus_loader = extractor.get_corpus_loader()
corpus_loader.trigger_event('update')
```

---

### ContextExtractor.get_mutable_corpora

Returns the corpora object that contains the loaded corpus objects.
This allows adding to the corpora from outside the CorpusLoader as the object returned is mutable, not a copy.
The Corpora object has a unique name constraint, meaning a corpus object cannot be added to the corpora if another corpus with the same name is already present. The same constraint applies to the rename method of corpus objects added to the corpora.

Returns: TCorpora - the mutable corpora object that contains the loaded corpus objects

Example

```python
extractor = ContextExtractor(run_logger=True)
corpora_object = extractor.get_mutable_corpora()
corpus = corpora_object.get("example")
```

---

## Example usage

The following snippet could be used as a cell in a Jupyter notebook.

```python
from atap_context_extractor import ContextExtractor
from atap_corpus_loader import CorpusLoader

loader = CorpusLoader(root_directory='example_dir', include_meta_loader=True, run_logger=True)
context_extractor: ContextExtractor = ContextExtractor(corpus_loader=loader, run_logger=True)
context_extractor.servable()
```
