import time
from typing import List
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import CLASSIFY_OCCURS_AT_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.prompts import CLASSIFY_OCCURS_AT_PROMPT
from scripts.schemas import AttackPhaseID, Relationship, RelationshipType

class OccursAtRelationship(BaseModel):
    """
    Represents a single discovered lifecycle orientation link pointing to an attack phase.
    """
    phase_id: AttackPhaseID = Field(
        description="The specific Attack Phase node where the technique executes (training or inference)."
    )
    justification: str = Field(
        description="A brief sentence connecting the technique description or case study lifecycle details directly to this phase."
    )

class OccursAtClassification(BaseModel):
    """
    The full payload structure returned from Mistral containing all discovered operational phases.
    """
    phases: List[OccursAtRelationship] = Field(
        description="List of valid OCCURS_AT relationships directly supported by graph data. Must contain at least one phase."
    )
    reasoning: str = Field(
        description="High-level lifecycle logic tracking whether the attack occurs pre-deployment or post-deployment."
    )

class OccursAtClassifier(BaseRelationshipClassifier):
    """
    Spins through techniques to isolate whether their mechanics operate during training or live inference.
    """
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm)
        self.context_cypher_read = CLASSIFY_OCCURS_AT_CONTEXT_QUERY  
        self.prompt_template = CLASSIFY_OCCURS_AT_PROMPT              
            
    def build_graph_context(self, technique_id: str) -> str | None:
        """
        Gathers bidirectional neighborhood properties to construct an explicit tracking window for the technique.
        """
        records, _, _ = self.graph_store.client.execute_query(
            self.context_cypher_read, technique_id=technique_id
        )
        
        if not records or not records[0].get('t'):
            return None
        
        record = records[0]
        technique_props = dict(record.get('t', {}).items()) if record.get('t') else {}
        neighborhood_map = record.get('neighborhood_map', [])

        graph_context = f"Target Link Evaluation: ({technique_id}) -[OCCURS_AT]-> (Attack Phases)\n\n"
        graph_context += f"Source Technique Attributes: {technique_props}\n\n"
        
        graph_context += "Target Technique Local Neighborhood Context (Operational Footprint):\n"
        if not neighborhood_map:
            graph_context += "  - No immediate surrounding context links found.\n"
        for entry in neighborhood_map:
            if entry.get('rel_type'):
                labels_str = ", ".join(entry['neighbor_labels'])
                graph_context += f"  - Technique relates via '{entry['rel_type']}' to Node({labels_str}) with properties: {entry['neighbor_props']}\n"
                
        return graph_context
        
    def process_single_relationship(self, graph_context: str, technique_id: str) -> List[Relationship] | None:
        """
        Executes structural inference on the lifecycle criteria and maps the response onto our domain schema.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=OccursAtClassification,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                classification: OccursAtClassification = program(
                    graph_context=graph_context,
                    technique_id=technique_id
                )

                self.print_raw_llm_output(technique_id, classification)

                relationships = []
                for link in classification.phases:
                    rel_node = Relationship(
                        source=technique_id,
                        target=link.phase_id.value,
                        relationship_type=RelationshipType.OCCURS_AT,
                        description=link.justification.strip()
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

    def print_raw_llm_output(self, technique_id: str, classification: OccursAtClassification) -> None:
        """
        Outputs clean text block summaries reflecting structural validation data straight to terminal stdout.
        """
        print("\n" + "="*80)
        print(f"CLASSIFICATION REPORT: ({technique_id}) -> (OCCURS_AT mappings)")
        print("="*80)
        
        print("\n[FIELD: phases]")
        if not classification or not classification.phases:
            print("  - No lifecycle phases mapped.")
        else:
            for link in classification.phases:
                print(f"  - Target Phase: {link.phase_id.value.upper()}")
                print(f"    Operational Context: {link.justification.strip()}")

        print("\n[FIELD: reasoning]")
        if classification:
            print(f"  {classification.reasoning.strip()}")
            
        print("="*80 + "\n")

    def process_all_relationships(self) -> List[Relationship]:
        """
        Pulls down every active technique profile saved in the system graph and streams them through evaluation.
        """
        find_pairs_query = """
        MATCH (t:Technique)
        RETURN t.id AS tech_id
        """

        print("Searching database for target techniques...")
        records, _, _ = self.graph_store.client.execute_query(find_pairs_query)

        total_techniques = len(records)
        print(f"Found {total_techniques} techniques to evaluate.\n")

        results: List[Relationship] = []

        for index, record in enumerate(records, start=1):
            tech_id = record["tech_id"]

            print(f"[{index}/{total_techniques}] Analyzing Lifecycle Vectors For: ({tech_id})")

            try:
                graph_context = self.build_graph_context(tech_id)

                if not graph_context:
                    print(f"  Warning: Could not retrieve details for technique {tech_id}. Skipping.")
                    continue

                relationships = self.process_single_relationship(graph_context, tech_id)

                if relationships:
                    print(f"  Determined Phase Mappings: {[r.target for r in relationships]}")
                    results.extend(relationships)

            except Exception as err:
                print(f"  Failed processing lifecycle mappings for {tech_id}: {err}")

            print("-" * 40)
            time.sleep(2.5)

        return results

if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    occurs_at_classifier = OccursAtClassifier(graph_store, llm)
    
    graph_context = occurs_at_classifier.build_graph_context(technique_id)
    
    if graph_context:
        occurs_at_classifier.process_single_relationship(graph_context, technique_id)