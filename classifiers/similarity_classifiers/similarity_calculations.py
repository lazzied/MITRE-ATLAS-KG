from typing import Any, Dict, Set


class TechniqueSimilarityCalculations:
    def __init__(self):
            # intuitive Jaccard index weights;
        self.weight_alters = 0.35       # Active modification footprint in the ML pipeline
        self.weight_access = 0.35       # Prerequisite infrastructure visibility
        self.weight_occurs_at = 0.15    # Environment timeline context (Training vs Inference)
        self.weight_achieves = 0.15     # Strategic tactical objective alignment
        
        # Hierarchical proximity adjustments; this is when two techniques share the same parent
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
