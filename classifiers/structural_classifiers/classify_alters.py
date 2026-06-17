import time
from typing import List
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import TECHNIQUE_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.llm_schemas import AltersResponseSchema
from scripts.classifiers.prompts import ALTERS_PROMPT
from scripts.schemas import EntityBooleanType, EntityType, Relationship, RelationshipType


class AltersClassifier(BaseRelationshipClassifier):
    """
    Spins through techniques to isolate what components of the machine learning system they modify or manipulate.
    """
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm, context_cypher_read=TECHNIQUE_CONTEXT_QUERY)
        self.prompt_template = ALTERS_PROMPT              
            
    def process_single_relationship(self, source_id: str, target_id: str | None = None) -> List[Relationship] | None:
        """
        Executes structural inference on the component alteration criteria and maps the response onto our domain schema.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=AltersResponseSchema,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        # FIXED: Context builder decoupled from loops and integrated natively here
        graph_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.SOURCE,
            entity_id=source_id,
            entity_type=EntityType.TECHNIQUE
        )

        for attempt in range(3):
            try:
                response_schema: AltersResponseSchema = program(
                    graph_context=graph_context,
                    technique_id=source_id
                )

                relationships = []
                for link in response_schema.entity_relationships:
                    rel_node = Relationship(
                        source=source_id,
                        target=link.target_entity.value,
                        relationship_type=RelationshipType.ALTERS,
                        description=link.description.strip()
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
        Pulls down every active technique profile saved in the system graph and streams them through evaluation.
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
                # FIXED: Streaming pure keys straight down to the single extraction wrapper
                relationships = self.process_single_relationship(source_id=tech_id)

                if relationships:
                    results.extend(relationships)

            except Exception as err:
                print(f"  Failed processing ALTERS relationship {tech_id}: {err}")

            time.sleep(2.5)

        return results


if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    alters_classifier = AltersClassifier(graph_store, llm)
    
    # FIXED: Direct verification execution mapping cleanly into runtime validation pipelines
    relationships = alters_classifier.process_single_relationship(source_id=technique_id)
    if relationships:
        print(f"Successfully processed {len(relationships)} structural modification/alteration links.")