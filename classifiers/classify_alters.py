import time
from typing import List
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import ALTERS_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.prompts import ALTERS_PROMPT
from scripts.schemas import ModelComponentID, Relationship, RelationshipType

class AltersRelationship(BaseModel):
    """
    Represents a single discovered modification link pointing to an impacted model component.
    """
    component_id: ModelComponentID = Field(
        description="The specific Model Component node that is altered, modified, poisoned, or perturbed by the technique."
    )
    required: bool = Field(
        description="True if the technique explicitly and definitely requires altering this component. False if altering it is conditional, or sometimes required."
    )
    component_justification: str = Field(
        description="Brief explanation highlighting how the technique alters or manipulates this component based on graph context data."
    )

class AltersClassification(BaseModel):
    """
    The full payload structure returned from Mistral containing all discovered model target components.
    """
    alters_requirements: List[AltersRelationship] = Field(
        description="List of valid ALTERS connections. Omit any components that fall under 'Not required' / 'No relationship'."
    )
    reasoning: str = Field(
        description="High-level evaluation logic tying the graph context evidence to the final component alteration mappings."
    )

class AltersClassifier(BaseRelationshipClassifier):
    """
    Spins through techniques to isolate what components of the machine learning system they modify or manipulate.
    """
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm)
        self.context_cypher_read = ALTERS_QUERY  
        self.prompt_template = ALTERS_PROMPT              
            
    def build_graph_context(self, technique_id: str) -> str | None:
        """
        Gathers contextual metadata from surrounding nodes to form an explicit tracking window for the technique.
        """
        records, _, _ = self.graph_store.client.execute_query(
            self.context_cypher_read, technique_id=technique_id
        )
        
        if not records or not records[0].get('t'):
            return None
        
        record = records[0]
        technique_props = dict(record.get('t', {}).items()) if record.get('t') else {}
        neighborhood_map = record.get('neighborhood_map', [])

        graph_context = f"Target Technique Node:\nID: {technique_id}\nAttributes: {technique_props}\n\n"
        graph_context += "Connected Neighborhood Topology & Case Evidence:\n"
        
        if not neighborhood_map:
            graph_context += "  - No immediate surrounding context links found.\n"
        for entry in neighborhood_map:
            if entry.get('rel_type'):
                labels_str = ", ".join(entry['neighbor_labels'])
                graph_context += f"  - [:{entry['rel_type']}] -> Node({labels_str}) | Properties: {entry['neighbor_props']}\n"
                
        return graph_context
        
    def process_single_relationship(self, graph_context: str, technique_id: str) -> List[Relationship] | None:
        """
        Executes structural inference on the component alteration criteria and maps the response onto our domain schema.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=AltersClassification,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                classification: AltersClassification = program(
                    graph_context=graph_context,
                    technique_id=technique_id
                )

                self.print_raw_llm_output(technique_id, classification)

                relationships = []
                for link in classification.alters_requirements:
                    rel_node = Relationship(
                        source=technique_id,
                        target=link.component_id.value,
                        relationship_type=RelationshipType.ALTERS,
                        description=link.component_justification.strip(),
                        required=link.required
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

    def print_raw_llm_output(self, technique_id: str, classification: AltersClassification = None) -> None:
        """
        Outputs clean text block summaries reflecting structural validation data straight to terminal stdout.
        """
        print("\n" + "="*80)
        print(f"CLASSIFICATION REPORT: ({technique_id}) -> (ALTERS mappings)")
        print("="*80)
        
        print("\n[FIELD: alters_requirements]")
        if not classification or not classification.alters_requirements:
            print("  - No ALTERS relationships identified in this context window.")
        else:
            for link in classification.alters_requirements:
                status_tag = "REQUIRED" if link.required else "SOMETIMES REQUIRED"
                print(f"  - Target Component: {link.component_id.value} [{status_tag}]")
                print(f"    Contextual Use: {link.component_justification.strip()}")

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

            print(f"[{index}/{total_techniques}] Analyzing Component Alteration Vectors For: ({tech_id})")

            try:
                graph_context = self.build_graph_context(tech_id)

                if not graph_context:
                    print(f"  Warning: Could not retrieve details for technique {tech_id}. Skipping.")
                    continue

                relationships = self.process_single_relationship(graph_context, tech_id)

                if relationships:
                    print(f"  Determined Component Mappings: {[r.target for r in relationships]}")
                    results.extend(relationships)

            except Exception as err:
                print(f"  Failed processing ALTERS mappings for {tech_id}: {err}")

            print("-" * 40)
            time.sleep(2.5)

        return results

if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    alters_classifier = AltersClassifier(graph_store, llm)
    
    graph_context = alters_classifier.build_graph_context(technique_id)
    
    if graph_context:
        alters_classifier.process_single_relationship(graph_context, technique_id)

