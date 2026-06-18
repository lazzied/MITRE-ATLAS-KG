import time
from typing import List
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import TECHNIQUE_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.llm_schemas import OccursAtResponseSchema
from scripts.classifiers.prompts import OCCURS_AT_PROMPT
from scripts.schemas import EntityBooleanType, EntityType, Relationship, RelationshipType


class OccursAtClassifier(BaseRelationshipClassifier):
    """
    Spins through techniques to isolate whether their mechanics operate during training or live inference.
    """
    def __init__(self, graph_store, llm, include_reasoning: bool = False):
        super().__init__(graph_store, llm, context_cypher_read=TECHNIQUE_CONTEXT_QUERY, include_reasoning=include_reasoning)
        self.prompt_template = OCCURS_AT_PROMPT              
            
    def process_single_relationship(self, source_id: str) -> List[Relationship] | None:
        """
        Executes structured LLM inference on a technique's graph context to discover OCCURS_AT lifecycle linkages.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=OccursAtResponseSchema,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        # FIXED: Context generation moved inside method with correct positional arguments
        graph_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.SOURCE,
            entity_id=source_id,
            entity_type=EntityType.TECHNIQUE
        )

        for attempt in range(3):
            try:
                classifier: OccursAtResponseSchema = program(
                    graph_context=graph_context,
                    technique_id=source_id
                )

                relationships = []
                for link in classifier.entity_relationships:
                    rel_node = Relationship(
                        source=source_id,
                        target=link.target_entity.value,
                        relationship_type=RelationshipType.OCCURS_AT,
                        description=link.description.strip(),
                        reasoning=link.reasoning if self.include_reasoning else None,
                    )
                    relationships.append(rel_node)

                return relationships

            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit. Hold on, retrying in a bit... (Attempt {attempt+1}/3)")
                    time.sleep(10)
                else:
                    raise e
                    
        return None

    def process_all_relationships(self) -> List[Relationship]:
        """
        Finds all system techniques, batches them through inference, and outputs enriched lifecycle relationship objects.
        """
        find_pairs_query = """
        MATCH (t:Technique)
        RETURN t.id AS tech_id
        """

        records, _, _ = self.graph_store.client.execute_query(find_pairs_query)
        results: List[Relationship] = []

        for index, record in enumerate(records, start=1):
            tech_id = record["tech_id"]

            try:
                # FIXED: Standardized call passing the identifier key directly
                relationships = self.process_single_relationship(source_id=tech_id)
                
                if relationships:
                    results.extend(relationships)

            except Exception as err:
                print(f"  Failed processing OCCURS_AT relationship {tech_id}: {err}")

            time.sleep(2.5)

        return results


if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    occurs_at_classifier = OccursAtClassifier(graph_store, llm)
    
    # FIXED: Direct validation workflow matching runtime testing standards
    relationships = occurs_at_classifier.process_single_relationship(source_id=technique_id)
    if relationships:
        print(f"Successfully processed {len(relationships)} execution lifecycle mapping links.")
