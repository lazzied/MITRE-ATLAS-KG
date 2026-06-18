import time
from typing import List
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import TECHNIQUE_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.llm_schemas import ViolatesResponseSchema
from scripts.classifiers.prompts import VIOLATES_PROMPT
from scripts.schemas import EntityBooleanType, EntityType, Relationship, RelationshipType


class ViolatesClassifier(BaseRelationshipClassifier):
    """
    Evaluates techniques to discover structural violations pointing to impacted security objectives.
    """
    def __init__(self, graph_store, llm, include_reasoning: bool = False):
        # Passes the generic query straight up to our base infrastructure
        super().__init__(graph_store, llm, context_cypher_read=TECHNIQUE_CONTEXT_QUERY, include_reasoning=include_reasoning)
        self.prompt_template = VIOLATES_PROMPT
        
    def process_single_relationship(self, source_id: str, target_id: str | None = None) -> List[Relationship] | None:
        """
        Executes structured LLM inference on a technique's graph context to discover VIOLATES linkages.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=ViolatesResponseSchema,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )
        
        # FIXED: Param ordering perfectly aligned to: (entity_boolean_type, entity_id, entity_type)
        graph_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.SOURCE,
            entity_id=source_id,
            entity_type=EntityType.TECHNIQUE
        )

        for attempt in range(3):
            try:
                classifier: ViolatesResponseSchema = program(
                    graph_context=graph_context,
                    technique_id=source_id,
                )

                relationships = []
                for link in classifier.entity_relationships:
                    rel = Relationship(
                        source=source_id,
                        target=link.target_entity.value,
                        relationship_type=RelationshipType.VIOLATES,
                        description=" , ".join(link.descriptions),
                        reasoning=link.reasoning if self.include_reasoning else None,
                    )
                    relationships.append(rel)

                return relationships

            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit. Hold on, retrying in a bit... (Attempt {attempt+1}/3)")
                    time.sleep(10)
                else:
                    raise e
                    
        return None

    def process_all_relationships(self, on_relationship=None) -> List[Relationship]:
        """
        Finds techniques, batches them through inference, and outputs enriched custom schema objects.
        """
        find_pairs_query = """
        MATCH (t:Technique)
        RETURN t.id AS tech_id
        """
        print("Loading techniques...")
        records, _, _ = self.graph_store.client.execute_query(find_pairs_query)
        if not records:
            raise RuntimeError("Technique query returned no rows. Stopping.")

        total_relations = len(records)
        results: List[Relationship] = []

        for index, record in enumerate(records, start=1):
            tech_id = record["tech_id"]
            if index == 1 or index % 10 == 0 or index == total_relations:
                print(f"Processing technique {index}/{total_relations}...")

            try:
                relationships = self.process_single_relationship(source_id=tech_id)
                if relationships is None:
                    raise RuntimeError("Warning: empty LLM response. Stopping.")

                if relationships:
                    results.extend(relationships)
                    if on_relationship:
                        for relationship in relationships:
                            on_relationship(relationship)

            except Exception as err:
                print(f"Mistral or classifier failed for VIOLATES {tech_id}: {err}")
                raise

            time.sleep(2.5)

        return results


if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    violates_classifier = ViolatesClassifier(graph_store, llm)
    
    # FIXED: Clean verification block mapping to the refactored workflow
    relationships = violates_classifier.process_single_relationship(source_id=technique_id)
    if relationships:
        print(f"Successfully processed {len(relationships)} structural violation links.")
