import time
from typing import Dict, List
from pydantic import BaseModel, Field
from pathlib import Path
import sys

from llama_index.core.program import LLMTextCompletionProgram

from context_queries import CLASSIFY_MITIGATION_CONTEXT_QUERY
from initialization import get_connections
from interface import BaseRelationshipClassifier
from prompts import CLASSIFY_MITIGATION_PROMPT

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from schemas import MitigationCategoryType, Relationship, RelationshipType 

class RelationshipClassification(BaseModel):
    categories: List[MitigationCategoryType] = Field(
        description="List of applicable category types for this MITIGATES relationship. Multiple entries are only allowed if there is strong, undeniable evidence."
    )
    category_descriptions: Dict[MitigationCategoryType, str] = Field(
        description="A dictionary mapping each selected category to a brief, specific explanation of how the mitigation works in that context."
    )
    reasoning: str = Field(
        description="Overall high-level cybersecurity logical justification for the classification choices."
    )

class MitigationClassifier(BaseRelationshipClassifier):
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm)
        self.context_cypher_read = CLASSIFY_MITIGATION_CONTEXT_QUERY  
        self.prompt_template = CLASSIFY_MITIGATION_PROMPT              
            
    def build_graph_context(self, mitigation_id: str, technique_id: str):
        records, _, _ = self.graph_store.client.execute_query(
            self.context_cypher_read, mitigation_id=mitigation_id, technique_id=technique_id
        )
        
        if not records:
            return None
        
        record = records[0]
        mitigation_props = dict(record.get('m', {}).items()) if record.get('m') else {}
        technique_props = dict(record.get('t', {}).items()) if record.get('t') else {}
        
        mitigation_context_map = record.get('mit_context', [])
        technique_context_map = record.get('tech_context', [])

        graph_context = f"Target Link: ({mitigation_id}) -[MITIGATES]-> ({technique_id})\n\n"
        graph_context += f"Source Mitigation Attributes: {mitigation_props}\n"
        graph_context += f"Target Technique Attributes: {technique_props}\n\n"
        
        graph_context += "Source Mitigation Local Neighborhood Context:\n"
        if not mitigation_context_map:
            graph_context += "  - No immediate surrounding context links found.\n"
        for item in mitigation_context_map:
            if item.get('rel'):
                graph_context += f"  • Mitigation relates via '{item['rel']}' to a node with properties: {item['neighbor']}\n"
                
        graph_context += "\nTarget Technique Behavioral Execution Context (Attack Path Footprint):\n"
        if not technique_context_map:
            graph_context += "  - No operational behavior context links found.\n"
            
        for item in technique_context_map:
            if item.get('rel'):
                graph_context += f"  • Technique relates via '{item['rel']}' to a node with properties: {item['neighbor']}\n"
                
        return graph_context
        
    def process_single_relationship(self, graph_context: str, mitigation_id: str, technique_id: str) -> Relationship | None:
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=RelationshipClassification,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                classification: RelationshipClassification = program(
                    graph_context=graph_context,
                    mitigation_id=mitigation_id,
                    technique_id=technique_id
                )

                self.print_raw_llm_output(mitigation_id, technique_id, classification)

                description = " | ".join(
                    f"[{cat.value.upper()}] {desc}"
                    for cat, desc in classification.category_descriptions.items()
                )

                return Relationship(
                    source=mitigation_id,
                    target=technique_id,
                    relationship_type=RelationshipType.MITIGATES,
                    description=description,
                    mitigation_type=classification.categories,
                )

            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit. Hold on, retrying in a bit... (Attempt {attempt+1}/3)")
                    time.sleep(10)
                else:
                    raise e
                    
        return None

    def print_raw_llm_output(self, mitigation_id: str, technique_id: str, classification: RelationshipClassification):
            print("\n" + "="*80)
            print(f"CLASSIFICATION REPORT: ({mitigation_id}) -> ({technique_id})")
            print("="*80)
            
            print("\n[FIELD: categories]")
            print(f"  {[cat.value.upper() for cat in classification.categories]}")

            print("\n[FIELD: reasoning]")
            print(f"  {classification.reasoning.strip()}")

            print("\n[FIELD: category_descriptions]")
            for category, description in classification.category_descriptions.items():
                print(f"  - [{category.value.upper()}]: {description.strip()}")
                
            print("="*80 + "\n")

    def process_all_relationships(self) -> list[Relationship]:
        find_pairs_query = """
        MATCH (m:Mitigation)-[r:MITIGATES]->(t:Technique)
        RETURN m.id AS mit_id, t.id AS tech_id
        """

        print("Searching database for relationship pairs...")
        records, _, _ = self.graph_store.client.execute_query(find_pairs_query)

        total_relations = len(records)
        print(f"Found {total_relations} relationships to evaluate.\n")

        results: list[Relationship] = []

        for index, record in enumerate(records, start=1):
            mit_id = record["mit_id"]
            tech_id = record["tech_id"]

            print(f"[{index}/{total_relations}] Analyzing Link: ({mit_id}) -> ({tech_id})")

            try:
                graph_context = self.build_graph_context(mit_id, tech_id)

                if not graph_context:
                    print(f" Warning: Could not retrieve graph details for {mit_id} -> {tech_id}. Skipping.")
                    continue

                relationship = self.process_single_relationship(graph_context, mit_id, tech_id)

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
    
    graph_context = mitigation_classifier.build_graph_context(mitigation_id, technique_id)
    
    if graph_context:
        mitigation_classifier.process_single_relationship(graph_context, mitigation_id, technique_id)

