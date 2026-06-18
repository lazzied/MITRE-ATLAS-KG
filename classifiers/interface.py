from abc import ABC, abstractmethod
from typing import List, Any
from scripts.schemas import EntityBooleanType, EntityType
from scripts.classifiers.context_queries import CASE_STUDY_QUERY, MITIGATION_CONTEXT_QUERY, TECHNIQUE_CONTEXT_QUERY


ENTITY_CONTEXT_QUERIES = {
    EntityType.CASE_STUDY: CASE_STUDY_QUERY,
    EntityType.MITIGATION: MITIGATION_CONTEXT_QUERY,
    EntityType.TECHNIQUE: TECHNIQUE_CONTEXT_QUERY,
}


class BaseRelationshipClassifier(ABC):

    def __init__(self, graph_store, llm, context_cypher_read, include_reasoning: bool = False):
        self.graph_store = graph_store
        self.llm = llm
        self.context_cypher_read = context_cypher_read
        self.include_reasoning = include_reasoning
        
    def get_context_from_entity(self, entity_id: str, entity_type: EntityType | None = None):
        context_cypher_read = ENTITY_CONTEXT_QUERIES.get(entity_type, self.context_cypher_read)
        records, _, _ = self.graph_store.client.execute_query(
            context_cypher_read, entity_id=entity_id
        )
        
        if not records or not records[0].get('source_node'):
            return [], {}
        
        record = records[0]
        topology = record.get('topology', [])
        entity_properties = dict(record.get('source_node', {}).items())
        
        return topology, entity_properties
    
    def build_context_prompt_from_entity(self,
                                         entity_boolean_type: EntityBooleanType, #either a target or source
                                         entity_id: str,
                                         entity_type: EntityType) -> str:
        
        topology, entity_properties = self.get_context_from_entity(entity_id, entity_type)
        
        context_prompt = ""
                
        context_prompt += f"{entity_boolean_type.value} ENTITY: {entity_type.value}\nID: {entity_id}\nAttributes: {entity_properties}\n\n"
        context_prompt += f"LOCAL GRAPH EDGE TOPOLOGY WITH SURROUNDING ENTITIES:\n"

        for edge in topology:
            if edge.get('rel_type'):
                target_labels_str = ", ".join(edge['target_labels'])
                
                context_prompt += f"- {entity_boolean_type.value} Node({entity_type.value}) relates via '{edge['rel_type']}' to Node({target_labels_str}) with properties: {edge['target_props']}\n"
                
        return context_prompt
    
    @abstractmethod
    def process_single_relationship(self, source_id: str, target_id: str | None = None) -> Any | None:
        """
        Runs structured LLM inference on a single node pair's graph context 
        and maps the output payload onto a structured Python domain schema.
        """
        pass


    @abstractmethod
    def process_all_relationships(self, on_relationship=None) -> List[Any]:
        """
        Finds pairs, batches them through inference, and outputs enriched custom schema objects.
        """
        pass
