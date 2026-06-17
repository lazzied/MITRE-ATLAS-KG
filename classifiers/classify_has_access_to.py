import time
from typing import List
from pydantic import BaseModel, Field

from llama_index.core.program import LLMTextCompletionProgram

from scripts.classifiers.context_queries import HAS_ACCESS_TO_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.prompts import HAS_ACCESS_TO_PROMPT

from scripts.schemas import ModelComponentID, Relationship, RelationshipType 

class AccessRelationship(BaseModel):
    component_id: ModelComponentID = Field(
        description="The specific Model Component node the technique requires or benefits from access to."
    )
    required: bool = Field(
        description="True if the technique absolutely cannot be performed without it. False if it is optional, conditional, or helpful."
    )
    component_justification: str = Field(
        description="Brief explanation highlighting how the technique uses this component, drawing from descriptions or case study metrics."
    )

class AccessClassification(BaseModel):
    access_requirements: List[AccessRelationship] = Field(
        description="List of valid HAS_ACCESS_TO connections. Omit any components that fall under 'No relationship'."
    )
    reasoning: str = Field(
        description="High-level evaluation logic tying the graph context evidence to the final component mappings."
    )

class AccessClassifier(BaseRelationshipClassifier):
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm)
        self.context_cypher_read = HAS_ACCESS_TO_CONTEXT_QUERY  
        self.prompt_template = HAS_ACCESS_TO_PROMPT              
            
    def build_graph_context(self, technique_id: str):
        records, _, _ = self.graph_store.client.execute_query(
            self.context_cypher_read, technique_id=technique_id
        )
        
        if not records or not records[0].get('t'):
            return None
        
        record = records[0]
        technique_props = dict(record.get('t', {}).items()) if record.get('t') else {}
        neighborhood_map = record.get('neighborhood_map', [])

        graph_context = f"Target Link Evaluation: ({technique_id}) -[HAS_ACCESS_TO]-> (Model Components)\n\n"
        graph_context += f"Source Technique Attributes: {technique_props}\n\n"
        
        graph_context += "Target Technique Local Neighborhood Context (Attack Path Footprint):\n"
        if not neighborhood_map:
            graph_context += "  - No immediate surrounding context links found.\n"
        for entry in neighborhood_map:
            if entry.get('rel_type'):
                labels_str = ", ".join(entry['neighbor_labels'])
                graph_context += f"  - Technique relates via '{entry['rel_type']}' to Node({labels_str}) with properties: {entry['neighbor_props']}\n"
                
        return graph_context
        
    def process_single_relationship(self, graph_context: str, technique_id: str) -> List[Relationship] | None:
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=AccessClassification,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                classification: AccessClassification = program(
                    graph_context=graph_context,
                    technique_id=technique_id
                )

                self.print_raw_llm_output(technique_id, classification)

                relationships = []
                for link in classification.access_requirements:
                    status_tag = "REQUIRED" if link.required else "OPTIONAL"
                    description = f"[{status_tag}] {link.component_justification}"

                    rel_node = Relationship(
                        source=technique_id,
                        target=link.component_id,
                        relationship_type=RelationshipType.HAS_ACCESS_TO,
                        description=description,
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

    def print_raw_llm_output(self, technique_id: str, classification: AccessClassification):
        print("\n" + "="*80)
        print(f"CLASSIFICATION REPORT: ({technique_id}) -> (HAS_ACCESS_TO mappings)")
        print("="*80)
        
        print("\n[FIELD: access_requirements]")
        if not classification.access_requirements:
            print("  - No access relationships mapped.")
        for link in classification.access_requirements:
            status = "REQUIRED" if link.required else "OPTIONAL"
            print(f"  - Target Component: {link.component_id.value.upper()} | Configuration: [{status}]")
            print(f"    Justification: {link.component_justification.strip()}")

        print("\n[FIELD: reasoning]")
        print(f"  {classification.reasoning.strip()}")
            
        print("="*80 + "\n")

    def process_all_relationships(self) -> list[Relationship]:
        find_pairs_query = """
        MATCH (t:Technique)
        RETURN t.id AS tech_id
        """

        print("Searching database for target techniques...")
        records, _, _ = self.graph_store.client.execute_query(find_pairs_query)

        total_techniques = len(records)
        print(f"Found {total_techniques} techniques to evaluate.\n")

        results: list[Relationship] = []

        for index, record in enumerate(records, start=1):
            tech_id = record["tech_id"]

            print(f"[{index}/{total_techniques}] Analyzing Access Vector Matrix For: ({tech_id})")

            try:
                graph_context = self.build_graph_context(tech_id)

                if not graph_context:
                    print(f"  Warning: Could not retrieve details for technique {tech_id}. Skipping.")
                    continue

                relationships = self.process_single_relationship(graph_context, tech_id)

                if relationships:
                    print(f"  Determined Access Mappings: {[r.target for r in relationships]}")
                    results.extend(relationships)

            except Exception as err:
                print(f"  Failed processing access vectors for {tech_id}: {err}")

            print("-" * 40)
            time.sleep(2.5)

        return results

if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    access_classifier = AccessClassifier(graph_store, llm)
    
    graph_context = access_classifier.build_graph_context(technique_id)
    
    if graph_context:
        access_classifier.process_single_relationship(graph_context, technique_id)
