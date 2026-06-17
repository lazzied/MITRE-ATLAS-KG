import time
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import TECHNIQUE_SIMILARITY_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.prompts import TECHNIQUE_SIMILARITY_PROMPT
from scripts.schemas import Relationship, RelationshipType
from atlas.schemas import TechniqueId

class TechniqueSimilarityRelationshipSchema():
    component_id: TechniqueId
    similarity_coeff: float
    reasoning: str = Field( description= "")

        

class TechniqueSimilarityLLMResponseSchema(BaseModel):
    
    reasoning: str = Field(
        description="A concise summary explaining why these two techniques are functionally similar based on their shared model components, visibility pre-requisites, lifecycle phases, and tactics."
    )   
    
class TechniqueSimilarityClassification(BaseRelationshipClassifier):
    """
    Computes a pairwise similarity matrix across ATLAS techniques using Jaccard indices, 
    and applies a generative LLM layer to justify and build the SIMILAR_TO relationship.
    """
    def __init__(self, graph_store, llm,similarity_calculations):
        super().__init__(graph_store, llm)
        self.context_cypher_read = TECHNIQUE_SIMILARITY_QUERY  
        self.prompt_template = TECHNIQUE_SIMILARITY_PROMPT   
        
        self.similarity_calculations =  similarity_calculations
        
    def build_context(self, technique_id: str) -> Dict[str, Any] | None:
        """
        Queries Neo4j via the unified graph client to fetch all target structural features.
        """
        records, _, _ = self.graph_store.client.execute_query(
            TECHNIQUE_SIMILARITY_QUERY, tech_id=technique_id
        )
        if not records or not records[0].get("t"):
            return None
            
        database_record = records[0]
        
        return {
            "tech_id": database_record["tech_id"],
            "achieves_set": set(database_record.get("associated_tactics", []) or []),
            "occurs_at_set": set(database_record.get("associated_phases", []) or []),
            "access_set": set(database_record.get("access_requirements", []) or []),
            "alters_set": set(database_record.get("alter_requirements", []) or []),
            "parent_id": database_record.get("parent_id")
        }

    
    def process_single_relationship(self, technique_id_1: str, technique_id_2: str) -> Relationship | None:
        """
        Executes mathematical matrix indexing, generates an LLM contextual justification text,
        and constructs the complete schema-validated Relationship object.
        """
        if self.llm is None:
            raise ValueError("An LLM instance must be provided to run process_single_relationship.")

        analysis = self.similarity_calculations.compute_technique_similarity(technique_id_1, technique_id_2)
        
        
        final_coef = analysis["final_score"]

        program = LLMTextCompletionProgram.from_defaults(
            output_cls=TechniqueSimilarityLLMResponseSchema,
            prompt_template_str=TECHNIQUE_SIMILARITY_PROMPT,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                llm_output: TechniqueSimilarityLLMResponseSchema = program(
                    technique_id_1=technique_id_1,
                    technique_id_2=technique_id_2,
                    final_score=final_coef,
                    profile_1=str(analysis["profiles"][0]),
                    profile_2=str(analysis["profiles"][1])
                )

                return Relationship(
                    source=technique_id_1,
                    target=technique_id_2,
                    relationship_type=RelationshipType.IS_SIMILAR_TO,
                    description=llm_output.justification.strip(),
                    similar_to_coef=final_coef
                )

            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit. Retrying in a bit... (Attempt {attempt+1}/3)")
                    time.sleep(10)
                else:
                    raise e
        return None

    def process_all_relationships(self, target_technique_id: str, top_n: int = 5, min_threshold: float = 0.40) -> List[Relationship]:
        """
        Coordinates the matrix row slice. Iterates over every technique node, evaluates raw similarity,
        filters against minimum thresholds, and generates descriptions for the high-confidence items.
        """
        find_all_query = "MATCH (t:Technique) RETURN t.id AS tech_id"
        records, _, _ = self.graph_store.client.execute_query(find_all_query)
        
        candidates = []
        for record in records:
            current_id = record["tech_id"]
            if current_id == target_technique_id:
                continue
                
            try:
                score_meta = self.similarity_calculations.compute_technique_similarity(target_technique_id, current_id)
                candidates.append((current_id, score_meta["final_score"]))
            except Exception:
                continue

        # Sort candidates descending by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Apply the hybrid strategy optimizations
        top_candidates = [c for c in candidates if c[1] >= min_threshold][:top_n]

        results: List[Relationship] = []
        if not top_candidates:
            print(f"No techniques met the minimum similarity threshold of {min_threshold} for {target_technique_id}.")
            return results

        print(f"Filtered down to top {len(top_candidates)} high-confidence similarity pairs.")
        
        for index, (peer_id, score) in enumerate(top_candidates, start=1):
            print(f"[{index}/{len(top_candidates)}] Processing link to peer: ({peer_id}) | Score: {score}")
            try:
                relationship = self.process_single_relationship(target_technique_id, peer_id)
                if relationship:
                    results.append(relationship)
            except Exception as err:
                print(f"  Failed generating similarity description for {peer_id}: {err}")
            time.sleep(1.5)

        return results

    def print_similarity_report(self, relationships: List[Relationship]) -> None:
        """
        Outputs clean structural component matrix metrics for the generated links straight to stdout.
        """
        print("\n" + "="*80)
        print(f"PROCESSED SIMILAR_TO RELATIONSHIP RECORDS MATRIX")
        print("="*80)
        
        if not relationships:
            print("  - No valid edges recorded or written for this configuration profile.")
        else:
            for index, rel in enumerate(relationships, start=1):
                print(f"[{index}] Edge: ({rel.source}) -[SIMILAR_TO]-> ({rel.target})")
                print(f"    Coefficient Metric (similar_to_coef) : {rel.similar_to_coef}")
                print(f"    LLM Architectural Justification       : {rel.description}")
                print("-" * 60)
        print("="*80 + "\n")


if __name__ == "__main__":
    graph_store, llm = get_connections()
    calculator = TechniqueSimilarityClassification(graph_store, llm)
    
    try:
        target_tech = "AML.T0051.002"
        
        # Runs calculations, enforces the 0.40 threshold, and caps results to top 5
        similarity_relationships = calculator.process_all_relationships(
            target_technique_id=target_tech, 
            top_n=5, 
            min_threshold=0.40
        )
        calculator.print_similarity_report(similarity_relationships)

    except Exception as error:
        print(f"Runtime Execution Error: {error}")