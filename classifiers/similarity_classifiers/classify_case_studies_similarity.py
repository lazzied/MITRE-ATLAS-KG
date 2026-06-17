import time
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import CASE_STUDY_SIMILARITY_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.prompts import CASE_STUDY_SIMILARITY_PROMPT
from scripts.schemas import Relationship, RelationshipType
from scripts.test.technique_similar_to_test import TechniqueSimilarityCalculator

class CaseStudyJustification(BaseModel):
    """
    Structured payload contract from the LLM validating operational campaign crossovers.
    """
    justification: str = Field(
        description="A concise narrative explaining the behavioral overlap between two case studies using their shared and highly similar techniques."
    )

class CaseStudySimilarityCalculator:
    """
    Computes a pairwise similarity matrix across historical case studies using a two-tier 
    technique overlap model, validated with a structured LLM explanation layer.
    """
    def __init__(self, graph_store, llm=None):
        self.graph_store = graph_store
        self.llm = llm
        # Instantiating the underlying technique engine to handle fallback matrix lookups
        self.tech_calculator = TechniqueSimilarityCalculator(graph_store, llm)
        
        # Two-tier blending weights
        self.weight_tier_1_exact = 0.60  # Weight given to identical technique overlaps
        self.weight_tier_2_soft = 0.40   # Weight given to proxied/similar technique behaviors

    def fetch_case_study_context(self, case_study_id: str) -> Dict[str, Any] | None:
        """
        Queries Neo4j to retrieve a case study and all of its utilized technique IDs.
        """
        query = CASE_STUDY_SIMILARITY_QUERY
        records, _, _ = self.graph_store.client.execute_query(query, case_id=case_study_id)
        
        if not records or not records[0].get("case_id"):
            return None
            
        record = records[0]
        return {
            "case_id": record["case_id"],
            "name": record["name"],
            "techniques": set(record["technique_ids"]) if record["technique_ids"] else set()
        }

    def compute_case_study_similarity(self, profile_1: Dict[str, Any], profile_2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the definitive blended similarity coefficient using exact intersections 
        and cross-compared technique similarity fallbacks.
        """
        set_a = profile_1["techniques"]
        set_b = profile_2["techniques"]

        # Edge case: If both case studies have no associated techniques recorded
        if not set_a and not set_b:
            return {"final_score": 1.0, "exact_shared": [], "soft_matched": []}
        if not set_a or not set_b:
            return {"final_score": 0.0, "exact_shared": [], "soft_matched": []}

        # --- Tier 1: Exact Technique Intersection ---
        exact_shared = set_a.intersection(set_b)
        tier_1_score = len(exact_shared) / len(set_a.union(set_b))

        # --- Tier 2: Soft Behavioral Cross-Match ---
        non_shared_a = set_a - exact_shared
        non_shared_b = set_b - exact_shared
        
        soft_match_scores = []
        soft_matched_details = []

        # Find the single closest technique match in the opposing pool for structural variants
        for tech_a in non_shared_a:
            best_score = 0.0
            best_peer = None
            for tech_b in non_shared_b:
                try:
                    # Look up peer technique proximity via the technique calculator matrix
                    analysis = self.tech_calculator.compute_technique_similarity(tech_a, tech_b)
                    score = analysis["final_score"]
                    if score > best_score:
                        best_score = score
                        best_peer = tech_b
                except Exception:
                    continue
            
            # Only record significant proxy similarities to reduce noise
            if best_score >= 0.30:
                soft_match_scores.append(best_score)
                soft_matched_details.append({"tech": tech_a, "matched_to": best_peer, "score": best_score})

        tier_2_score = sum(soft_match_scores) / len(soft_match_scores) if soft_match_scores else 0.0

        # --- Tier 3: Linear Blend Orchestration ---
        final_blended_score = (self.weight_tier_1_exact * tier_1_score) + (self.weight_tier_2_soft * tier_2_score)

        return {
            "comparison_pair": (profile_1["case_id"], profile_2["case_id"]),
            "names": (profile_1["name"], profile_2["name"]),
            "final_score": round(min(final_blended_score, 1.0), 4),
            "tier_1_exact_score": round(tier_1_score, 4),
            "tier_2_soft_score": round(tier_2_score, 4),
            "exact_shared_techniques": list(exact_shared),
            "soft_matched_pairs": soft_matched_details
        }

    def process_single_relationship(self, profile_1: Dict[str, Any], profile_2: Dict[str, Any]) -> Relationship | None:
        """
        Calculates mathematical metrics, formats structural prompt vectors, and triggers 
        the structured LLM completion program to build the case study edge.
        """
        if self.llm is None:
            raise ValueError("An LLM instance must be provided to run process_single_relationship.")

        analysis = self.compute_case_study_similarity(profile_1, profile_2)
        final_coef = analysis["final_score"]

        # Grounding template to instruct the LLM on exactly how to interpret the math matrix
        prompt_template = CASE_STUDY_SIMILARITY_PROMPT

        program = LLMTextCompletionProgram.from_defaults(
            output_cls=CaseStudyJustification,
            prompt_template_str=prompt_template,
            llm=self.llm,
            verbose=False
        )

        for attempt in range(3):
            try:
                llm_output: CaseStudyJustification = program(
                    final_score=final_coef,
                    name_1=profile_1["name"], id_1=profile_1["case_id"],
                    name_2=profile_2["name"], id_2=profile_2["case_id"],
                    exact_techniques=str(analysis["exact_shared_techniques"]),
                    soft_matches=str(analysis["soft_matched_pairs"])
                )

                return Relationship(
                    source=profile_1["case_id"],
                    target=profile_2["case_id"],
                    relationship_type=RelationshipType.SIMILAR_TO,
                    description=llm_output.justification.strip(),
                    similar_to_coef=final_coef
                )
            except Exception as e:
                if "429" in str(e):
                    time.sleep(10)
                else:
                    raise e
        return None

    def process_all_relationships(self, target_case_id: str, top_n: int = 5, min_threshold: float = 0.40) -> List[Relationship]:
        """
        Coordinates the matrix row slice for case studies. Compares target case study against 
        all alternative campaign records, sorts metrics, and creates high-confidence edges.
        """
        target_profile = self.fetch_case_study_context(target_case_id)
        if not target_profile:
            raise ValueError(f"Target Case Study '{target_case_id}' not found in the database.")

        find_all_query = "MATCH (c:CaseStudy) RETURN c.id AS case_id"
        records, _, _ = self.graph_store.client.execute_query(find_all_query)
        
        candidates = []
        for record in records:
            current_id = record["case_id"]
            if current_id == target_case_id:
                continue
                
            current_profile = self.fetch_case_study_context(current_id)
            if not current_profile:
                continue
                
            try:
                score_meta = self.compute_case_study_similarity(target_profile, current_profile)
                candidates.append((current_profile, score_meta["final_score"]))
            except Exception:
                continue

        # Sort matrix items descending by blended coefficient score
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [c for c in candidates if c[1] >= min_threshold][:top_n]

        results: List[Relationship] = []
        if not top_candidates:
            print(f"No case studies met the minimum similarity threshold of {min_threshold} for {target_case_id}.")
            return results

        print(f"Identified {len(top_candidates)} case studies for similarity mapping optimization.")
        
        for index, (peer_profile, score) in enumerate(top_candidates, start=1):
            print(f"[{index}/{len(top_candidates)}] Extrapolating link to: {peer_profile['name']} | Blended Score: {score}")
            try:
                relationship = self.process_single_relationship(target_profile, peer_profile)
                if relationship:
                    results.append(relationship)
            except Exception as err:
                print(f"  Inference error generation failed for {peer_profile['case_id']}: {err}")
            time.sleep(1.5)

        return results

    def print_similarity_report(self, relationships: List[Relationship]) -> None:
        """
        Outputs clean structural components straight to terminal stdout.
        """
        print("\n" + "="*80)
        print("CASE STUDY TO CASE STUDY SIMILARITY RELATIONSHIPS")
        print("="*80)
        
        if not relationships:
            print("  - No valid similarity boundaries met.")
        else:
            for index, rel in enumerate(relationships, start=1):
                print(f"[{index}] Edge: ({rel.source}) -[SIMILAR_TO]-> ({rel.target})")
                print(f"    Blended Similarity Coef : {rel.similar_to_coef}")
                print(f"    Threat Intel Summary    : {rel.description}")
                print("-" * 60)
        print("="*80 + "\n")


if __name__ == "__main__":
    graph_store, llm = get_connections()
    calculator = CaseStudySimilarityCalculator(graph_store, llm)
    
    try:
        # Example target case study to analyze across the global matrix
        target_study = "AML.CS0001" 
        
        relationships = calculator.process_all_relationships(
            target_case_id=target_study, 
            top_n=5, 
            min_threshold=0.40
        )
        calculator.print_similarity_report(relationships)

    except Exception as error:
        print(f"Runtime Execution Error: {error}")