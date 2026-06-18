import time
from typing import List
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import MITIGATION_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.llm_schemas import MitigationResponseSchema
from scripts.classifiers.prompts import MITIGATION_PROMPT
from scripts.schemas import EntityBooleanType, EntityType, Relationship, RelationshipType 


class MitigationClassifier(BaseRelationshipClassifier):
    """
    Evaluates established binary links between Mitigations and Techniques 
    to map architectural defense coverage domains.
    """
    def __init__(self, graph_store, llm, include_reasoning: bool = False):
        # Note: Ensure MITIGATION_CONTEXT_QUERY in your files targets $entity_id globally now!
        super().__init__(graph_store, llm, context_cypher_read=MITIGATION_CONTEXT_QUERY, include_reasoning=include_reasoning)
        self.prompt_template = MITIGATION_PROMPT              

    def process_single_relationship(self, source_id: str, target_id: str | None = None) -> Relationship | None:
        """
        Extracts structural attributes and graph topologies for both nodes to build an evaluation prompt.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=MitigationResponseSchema,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )
        
        # 1. Dynamically build context strings cleanly using your generic base methods
        mitigation_entity_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.SOURCE,
            entity_id=source_id,
            entity_type=EntityType.MITIGATION
        )
        
        technique_entity_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.TARGET,
            entity_id=target_id,
            entity_type=EntityType.TECHNIQUE
        )
        
        graph_context = mitigation_entity_context + "\n" + technique_entity_context
        
        for attempt in range(3):
            try:
                # Aligned payload tracking mapping directly to your final Pydantic Schema rules
                classifier: MitigationResponseSchema = program(
                    graph_context=graph_context,
                    mitigation_id=source_id,
                    technique_id=target_id
                )

                # Extracts relationships cleanly out of the unified inner target iterable list
                if not classifier.entity_relationships:
                    return None
                    
                target_rel = classifier.entity_relationships[0]

                return Relationship(
                    source=source_id,
                    target=target_id,
                    relationship_type=RelationshipType.MITIGATES,
                    description=target_rel.description,
                    mitigation_type=target_rel.categories,
                    reasoning=target_rel.reasoning if self.include_reasoning else None,
                )

            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit. Hold on, retrying in a bit... (Attempt {attempt+1}/3)")
                    time.sleep(10)
                else:
                    raise e
                    
        return None

    def process_all_relationships(self) -> List[Relationship]:
        """
        Finds pairs, executes independent context builders, and tracks the global system run profile.
        """
        find_pairs_query = """
        MATCH (m:Mitigation)-[:MITIGATES]->(t:Technique)
        RETURN m.id AS mit_id, t.id AS tech_id
        """

        print("Searching database for relationship pairs...")
        records, _, _ = self.graph_store.client.execute_query(find_pairs_query)

        total_relations = len(records)
        print(f"Found {total_relations} relationships to evaluate.\n")

        results: List[Relationship] = []

        for index, record in enumerate(records, start=1):
            mit_id = record["mit_id"]
            tech_id = record["tech_id"]

            print(f"[{index}/{total_relations}] Analyzing Link: ({mit_id}) -> ({tech_id})")

            try:
                # FIXED: Removed broken build_graph_context intermediary step. 
                # Keys pass directly through the uniform entry point.
                relationship = self.process_single_relationship(source_id=mit_id, target_id=tech_id)

                if relationship:
                    print(f"  Determined Classes: {[cat.value.upper() for cat in relationship.mitigation_type]}")
                    results.append(relationship)

            except Exception as err:
                print(f" Failed processing link {mit_id} -> {tech_id}: {err}")

            print("-" * 40)
            time.sleep(2.5)

        return results


if __name__ == "__main__":
    mitigation_id = "AML.M0033"
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    mitigation_classifier = MitigationClassifier(graph_store, llm)
    
    # FIXED: Direct clean verification pipeline test
    relationship = mitigation_classifier.process_single_relationship(source_id=mitigation_id, target_id=technique_id)
    if relationship:
        print(f"Successfully evaluated mapping link: {relationship.description}")
