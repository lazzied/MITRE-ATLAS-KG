import time
from typing import  List
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import VIOLATES_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.prompts import VIOLATES_PROMPT
from mappers import VIOLATES_RELATIONSHIP_DESCRIPTION
from scripts.schemas import Relationship, RelationshipType, SecurityObjectiveID


class ViolatesRelationship(BaseModel):
    """
    Represents a single discovered violation link pointing to an impacted security objective.
    """
    objective_id: SecurityObjectiveID = Field(
        description="The target Security Objective node that this technique violates."
    )
    descriptions: List[str] = Field(
        description="A list containing one or more exact predefined description strings corresponding to this objective type."
    )
    justification: str = Field(
        description="Clear, text-grounded cybersecurity reasoning detailing how the technique achieves these specific impacts."
    )

class ViolatesClassification(BaseModel):
    """
    The full payload structure returned from Mistral containing all mapped security objective violations.
    """
    violations: List[ViolatesRelationship] = Field(
        description="List of valid VIOLATES relationships directly supported by graph context. Omit objectives with no active violation."
    )
    reasoning: str = Field(
        description="High-level cognitive logic tracking the overall evaluation process across tactics and case studies."
    )

class ViolatesClassifier(BaseRelationshipClassifier):
    """
    Spins through techniques to analyze how they compromise Confidentiality, Integrity, or Availability.
    """
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm)
        self.context_cypher_read = VIOLATES_QUERY  
        self.prompt_template = VIOLATES_PROMPT              
            
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

        graph_context = f"TARGET TECHNIQUE NODE:\nID: {technique_id}\nAttributes: {technique_props}\n\n"
        graph_context += "CONNECTED NEIGHBORHOOD TOPOLOGY (TACTICS & CASE EVIDENCE):\n"
        
        if not neighborhood_map:
            graph_context += "  - No immediate surrounding context links found.\n"
        for entry in neighborhood_map:
            if entry.get('rel_type'):
                labels_str = ", ".join(entry['neighbor_labels'])
                graph_context += f"- [:{entry['rel_type']}] -> Node({labels_str}) | Properties: {entry['neighbor_props']}\n"
                
        return graph_context
        
    def process_single_relationship(self, graph_context: str, technique_id: str) -> List[Relationship] | None:
        """
        Executes structural inference on security objective violations and maps responses onto our domain schema.
        """
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=ViolatesClassification,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        conf_opts = "\n".join([f'- "{opt}"' for opt in VIOLATES_RELATIONSHIP_DESCRIPTION[SecurityObjectiveID.CONFIDENTIALITY]])
        int_opts = "\n".join([f'- "{opt}"' for opt in VIOLATES_RELATIONSHIP_DESCRIPTION[SecurityObjectiveID.INTEGRITY]])
        avail_opts = "\n".join([f'- "{opt}"' for opt in VIOLATES_RELATIONSHIP_DESCRIPTION[SecurityObjectiveID.AVAILABILITY]])

        for attempt in range(3):
            try:
                classification: ViolatesClassification = program(
                    graph_context=graph_context,
                    technique_id=technique_id,
                    confidentiality_options=conf_opts,
                    integrity_options=int_opts,
                    availability_options=avail_opts
                )

                self.print_raw_llm_output(technique_id, classification)

                relationships = []
                for link in classification.violations:
                    rel_node = Relationship(
                        source=technique_id,
                        target=link.objective_id.value,
                        relationship_type=RelationshipType.VIOLATES,
                        description=" | ".join(link.descriptions),
                        justification=link.justification.strip()
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

    def print_raw_llm_output(self, technique_id: str, classification: ViolatesClassification = None) -> None:
        """
        Outputs clean text block summaries reflecting structural validation data straight to terminal stdout.
        """
        print("\n" + "="*80)
        print(f"CLASSIFICATION REPORT: ({technique_id}) -> (VIOLATES mappings)")
        print("="*80)
        
        print("\n[FIELD: violations]")
        if not classification or not classification.violations:
            print("  - No VIOLATES links identified for this configuration.")
        else:
            for link in classification.violations:
                print(f"  - Target Objective: {link.objective_id.value.upper()}")
                print(f"    Assigned Attributes (descriptions): {link.descriptions}")
                print(f"    Line Evidence: {link.justification.strip()}")

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

            print(f"[{index}/{total_techniques}] Analyzing Security Violations For: ({tech_id})")

            try:
                graph_context = self.build_graph_context(tech_id)

                if not graph_context:
                    print(f"  Warning: Could not retrieve details for technique {tech_id}. Skipping.")
                    continue

                relationships = self.process_single_relationship(graph_context, tech_id)

                if relationships:
                    print(f"  Determined Mappings: {[r.target for r in relationships]}")
                    results.extend(relationships)

            except Exception as err:
                print(f"  Failed processing VIOLATES mappings for {tech_id}: {err}")

            print("-" * 40)
            time.sleep(2.5)

        return results

if __name__ == "__main__":
    technique_id = "AML.T0051.002"
    
    graph_store, llm = get_connections()
    violates_classifier = ViolatesClassifier(graph_store, llm)
    
    graph_context = violates_classifier.build_graph_context(technique_id)
    
    if graph_context:
        violates_classifier.process_single_relationship(graph_context, technique_id)