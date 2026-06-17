import time
from typing import Dict, Any, Set, List
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import TECHNIQUE_SIMILARITY_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.prompts import SIMILARITY_JUSTIFICATION_PROMPT
from scripts.schemas import Relationship, RelationshipType

class SimilarityJustification(BaseModel):
    """
    Structured payload contract from the LLM validating structural similarity traits.
    """
    justification: str = Field(
        description="A concise summary explaining why these two techniques are functionally similar based on their shared model components, visibility pre-requisites, lifecycle phases, and tactics."
    )

class TechniqueSimilarityCalculator:
    """
    Computes a pairwise similarity matrix across ATLAS techniques using Jaccard indices, 
    and applies a generative LLM layer to justify and build the SIMILAR_TO relationship.
    """
    def __init__(self, graph_store, llm=None):
        self.graph_store = graph_store
        self.llm = llm
        
        # Jaccard index weight assignments
        self.weight_alters = 0.35       # Active modification footprint in the ML pipeline
        self.weight_access = 0.35       # Prerequisite infrastructure visibility
        self.weight_occurs_at = 0.15    # Environment timeline context (Training vs Inference)
        self.weight_achieves = 0.15     # Strategic tactical objective alignment
        
        # Hierarchical proximity adjustments
        self.sibling_hierarchy_boost = 0.15

    def calculate_jaccard_index(self, set_a: Set[Any], set_b: Set[Any]) -> float:
        """
        Calculates the Jaccard similarity index between two standard Python sets.
        
        $$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$
        """
        if len(set_a) == 0 and len(set_b) == 0:
            return 1.0
        if len(set_a) == 0 or len(set_b) == 0:
            return 0.0
        
        overlapping_elements = set_a.intersection(set_b)
        all_unique_elements = set_a.union(set_b)
        return len(overlapping_elements) / len(all_unique_elements)

    def fetch_technique_relationships(self, technique_id: str) -> Dict[str, Any] | None:
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

    def calculate_base_weighted_score(self, overlaps: Dict[str, float]) -> float:
        """
        Performs the dimensional matrix multiplication across risk vectors.
        """
        return (
            (self.weight_alters * overlaps["alters_overlap"]) +
            (self.weight_access * overlaps["access_overlap"]) +
            (self.weight_occurs_at * overlaps["occurs_at_overlap"]) +
            (self.weight_achieves * overlaps["achieves_overlap"])
        )

    def apply_hierarchical_adjustments(self, base_score: float, are_siblings: bool) -> float:
        """
        Calculates parent node inheritance bonuses and caps the absolute metric.
        """
        if not are_siblings:
            return base_score
        final_score = base_score + self.sibling_hierarchy_boost
        return min(final_score, 1.0)

    def compute_technique_similarity(self, technique_id_1: str, technique_id_2: str) -> Dict[str, Any]:
        """
        Retrieves the profile vectors of both techniques, evaluates dimensional weights, 
        and calculates structural similarity adjusted for subtechnique hierarchies.
        """
        profile_1 = self.fetch_technique_relationships(technique_id_1)
        profile_2 = self.fetch_technique_relationships(technique_id_2)

        if profile_1 is None:
            raise ValueError(f"Technique ID '{technique_id_1}' was not found in the database.")
        if profile_2 is None:
            raise ValueError(f"Technique ID '{technique_id_2}' was not found in the database.")

        overlaps = {
            "alters_overlap": self.calculate_jaccard_index(profile_1["alters_set"], profile_2["alters_set"]),
            "access_overlap": self.calculate_jaccard_index(profile_1["access_set"], profile_2["access_set"]),
            "occurs_at_overlap": self.calculate_jaccard_index(profile_1["occurs_at_set"], profile_2["occurs_at_set"]),
            "achieves_overlap": self.calculate_jaccard_index(profile_1["achieves_set"], profile_2["achieves_set"])
        }

        weighted_base_score = self.calculate_base_weighted_score(overlaps)
        are_siblings = profile_1["parent_id"] is not None and profile_1["parent_id"] == profile_2["parent_id"]
        final_similarity_score = self.apply_hierarchical_adjustments(weighted_base_score, are_siblings)

        return {
            "comparison_pair": (technique_id_1, technique_id_2),
            "profiles": (profile_1, profile_2),
            "base_score": round(weighted_base_score, 4),
            "final_score": round(final_similarity_score, 4),
            "is_sibling_subtechnique": are_siblings,
            "metric_breakdown": {key: round(val, 4) for key, val in overlaps.items()}
        }

    def process_single_relationship(self, technique_id_1: str, technique_id_2: str) -> Relationship | None:
        """
        Executes mathematical matrix indexing, generates an LLM contextual justification text,
        and constructs the complete schema-validated Relationship object.
        """
        if self.llm is None:
            raise ValueError("An LLM instance must be provided to run process_single_relationship.")

        analysis = self.compute_technique_similarity(technique_id_1, technique_id_2)
        final_coef = analysis["final_score"]

        program = LLMTextCompletionProgram.from_defaults(
            output_cls=SimilarityJustification,
            prompt_template_str=SIMILARITY_JUSTIFICATION_PROMPT,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                llm_output: SimilarityJustification = program(
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
                score_meta = self.compute_technique_similarity(target_technique_id, current_id)
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
    calculator = TechniqueSimilarityCalculator(graph_store, llm)
    
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