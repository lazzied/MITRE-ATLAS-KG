from typing import Any, Dict, Set


class TechniqueSimilarityCalculations:
    def __init__(self):
        # These weights decide how much each shared graph signal contributes to similarity.
        self.weight_alters = 0.35
        self.weight_access = 0.35
        self.weight_occurs_at = 0.15
        self.weight_achieves = 0.15
        
        # Hierarchical proximity adjustments for explicit subtechnique mapping
        self.sibling_hierarchy_boost = 0.15
        
    def calculate_jaccard_index(self, set_a: Set[Any], set_b: Set[Any]) -> float:
        """
        Calculates the Jaccard similarity index between two standard Python sets.
        """
        if len(set_a) == 0 and len(set_b) == 0:
            return 1.0
        if len(set_a) == 0 or len(set_b) == 0:
            return 0.0
        
        shared_items = set_a.intersection(set_b)
        all_items = set_a.union(set_b)
        return len(shared_items) / len(all_items)
    
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
    
    def compute_technique_similarity(self, profile_1: Dict[str, Any], profile_2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates dimensional Jaccard indices across clean dictionary profiles.
        """
        if profile_1 is None or profile_2 is None:
            raise ValueError("Both technique profiles must be populated and valid dictionaries.")

        overlaps = {
            "alters_overlap": self.calculate_jaccard_index(profile_1["alters_set"], profile_2["alters_set"]),
            "access_overlap": self.calculate_jaccard_index(profile_1["access_set"], profile_2["access_set"]),
            "occurs_at_overlap": self.calculate_jaccard_index(profile_1["occurs_at_set"], profile_2["occurs_at_set"]),
            "achieves_overlap": self.calculate_jaccard_index(profile_1["achieves_set"], profile_2["achieves_set"])
        }

        base_similarity_score = self.calculate_base_weighted_score(overlaps)
        
        # Sibling subtechniques often behave alike, so they get a small boost.
        are_siblings = (
            profile_1.get("parent_id") is not None and 
            profile_1.get("parent_id") == profile_2.get("parent_id")
        )
        final_similarity_score = self.apply_hierarchical_adjustments(base_similarity_score, are_siblings)

        return {
            "comparison_pair": (profile_1["tech_id"], profile_2["tech_id"]),
            "base_score": round(base_similarity_score, 4),
            "final_score": round(final_similarity_score, 4),
            "is_sibling_subtechnique": are_siblings,
            "metric_breakdown": {key: round(val, 4) for key, val in overlaps.items()}
        }
        

class CaseStudySimilarityCalculations:
    
    def __init__(self, tech_calculator=None, weight_exact: float = 0.60, weight_soft: float = 0.40):
        self.weight_tier_1_exact = weight_exact
        self.weight_tier_2_soft = weight_soft
        
        # Internal instance fallback link to pure technique calculations
        self.tech_math = TechniqueSimilarityCalculations()
        
        # The higher-level database profile parser engine passing contextual data down
        self.tech_calculator = tech_calculator
        self._tech_profile_cache = {}
        self._tech_similarity_cache = {}

    def _get_technique_profile(self, technique_id: str) -> Dict[str, Any]:
        if technique_id not in self._tech_profile_cache:
            _, profile = self.tech_calculator.get_context_from_entity(technique_id)
            self._tech_profile_cache[technique_id] = profile
        return self._tech_profile_cache[technique_id]

    def _compute_soft_technique_similarity(self, source_technique: str, target_technique: str) -> float:
        pair_key = tuple(sorted((source_technique, target_technique)))
        if pair_key not in self._tech_similarity_cache:
            source_profile = self._get_technique_profile(source_technique)
            target_profile = self._get_technique_profile(target_technique)
            similarity_analysis = self.tech_math.compute_technique_similarity(source_profile, target_profile)
            self._tech_similarity_cache[pair_key] = similarity_analysis["final_score"]
        return self._tech_similarity_cache[pair_key]

    def compute_case_study_similarity(self, profile_1: Dict[str, Any], profile_2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the definitive blended similarity coefficient using exact intersections 
        and cross-compared technique similarity fallbacks.
        """
        source_techniques = profile_1["techniques"]
        target_techniques = profile_2["techniques"]

        if not source_techniques and not target_techniques:
            return {"final_score": 1.0, "exact_shared_techniques": [], "soft_matched_pairs": []}
        if not source_techniques or not target_techniques:
            return {"final_score": 0.0, "exact_shared_techniques": [], "soft_matched_pairs": []}

        # First, reward case studies that demonstrate the exact same techniques.
        exact_shared = source_techniques.intersection(target_techniques)
        
        technique_union_size = len(source_techniques.union(target_techniques))
        exact_overlap_score = len(exact_shared) / technique_union_size if technique_union_size > 0 else 0.0

        # Then, look for different techniques that are still behaviorally similar.
        source_only_techniques = source_techniques - exact_shared
        target_only_techniques = target_techniques - exact_shared
        
        soft_match_scores = []
        soft_matched_details = []

        for source_technique in source_only_techniques:
            best_score = 0.0
            best_matching_technique = None
            for target_technique in target_only_techniques:
                try:
                    if self.tech_calculator and hasattr(self.tech_calculator, 'get_context_from_entity'):
                        similarity_score = self._compute_soft_technique_similarity(source_technique, target_technique)
                        
                        if similarity_score > best_score:
                            best_score = similarity_score
                            best_matching_technique = target_technique
                except Exception:
                    continue
            
            # Keep meaningful behavioral overlaps
            if best_score >= 0.30:
                soft_match_scores.append(best_score)
                soft_matched_details.append({
                    "tech": source_technique,
                    "matched_to": best_matching_technique,
                    "score": best_score
                })

        soft_overlap_score = sum(soft_match_scores) / len(soft_match_scores) if soft_match_scores else 0.0

        # Blend exact overlap and softer behavioral overlap into one final score.
        final_blended_score = (self.weight_tier_1_exact * exact_overlap_score) + (self.weight_tier_2_soft * soft_overlap_score)

        return {
            "comparison_pair": (profile_1["case_id"], profile_2["case_id"]),
            "name_1": profile_1.get("name", "Unknown"),
            "name_2": profile_2.get("name", "Unknown"),
            "final_score": round(min(final_blended_score, 1.0), 4),
            "tier_1_exact_score": round(exact_overlap_score, 4),
            "tier_2_soft_score": round(soft_overlap_score, 4),
            "exact_shared_techniques": list(exact_shared),
            "soft_matched_pairs": soft_matched_details
        }
