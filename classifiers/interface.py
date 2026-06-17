from abc import ABC, abstractmethod
from typing import List, Any

class BaseRelationshipClassifier(ABC):
    """
    Abstract Base Interface contract ensuring all late-stage relationship enrichment 
    modules follow the exact same structural pattern.
    """
    def __init__(self, graph_store, llm):
        self.graph_store = graph_store
        self.llm = llm

    @abstractmethod
    def build_graph_context(self, source_id: str, target_id: str) -> str | None:
        """Queries database topology to assemble text context for the LLM."""
        pass

    @abstractmethod
    def process_single_relationship(self, graph_context: str, source_id: str, target_id: str) -> Any | None:
        """
        Runs structured LLM inference on a single node pair's graph context 
        and maps the output payload onto a structured Python domain schema.
        """
        pass

    @abstractmethod
    def print_raw_llm_output(self, source_id: str, target_id: str, classification: Any) -> None:
        """
        Intercepts the raw structured Pydantic object immediately after LLM inference 
        and prints its complete logical properties and fields to stdout for real-time reporting.
        """
        pass

    @abstractmethod
    def process_all_relationships(self) -> List[Any]:
        """Finds pairs, batches them through inference, and outputs enriched custom schema objects."""
        pass