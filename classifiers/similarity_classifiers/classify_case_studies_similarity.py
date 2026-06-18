import time
from typing import List
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import CASE_STUDY_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.llm_schemas import CaseStudySimilarityResponseSchema
from scripts.classifiers.prompts import CASE_STUDY_SIMILARITY_PROMPT
from scripts.classifiers.similarity_classifiers.classify_technique_similarity import TechniqueSimilarityCalculator
from scripts.classifiers.similarity_classifiers.similarity_calculations import CaseStudySimilarityCalculations
from scripts.schemas import EntityBooleanType, EntityType, Relationship, RelationshipType


class CaseStudySimilarityCalculator(BaseRelationshipClassifier):
    """
    Finds similar ATLAS case studies by comparing the techniques they demonstrate.
    """
    def __init__(self, graph_store, llm=None, tech_calculator=None, include_reasoning: bool = False):
        super().__init__(graph_store, llm, context_cypher_read=CASE_STUDY_QUERY, include_reasoning=include_reasoning)
        self.prompt_template = CASE_STUDY_SIMILARITY_PROMPT
        
        self.tech_calculator = tech_calculator or TechniqueSimilarityCalculator(graph_store, llm, include_reasoning=include_reasoning)
        
        self.similarity_calculations = CaseStudySimilarityCalculations(
            tech_calculator=self.tech_calculator,
            weight_exact=0.60,
            weight_soft=0.40
        )

    def get_context_from_entity(self, entity_id: str):
        topology, case_study_properties = super().get_context_from_entity(entity_id)
        if not case_study_properties:
            return topology, {}
        return topology, self._build_case_study_similarity_profile(entity_id, topology, case_study_properties)

    def _build_case_study_similarity_profile(self, case_study_id: str, topology, case_study_properties):
        profile = dict(case_study_properties)
        profile["case_id"] = profile.get("id", case_study_id)
        profile["techniques"] = set()

        # Each EMPLOYS edge contributes one technique to the comparison set.
        for edge in topology:
            target_properties = edge.get("target_props", {})
            technique_id = target_properties.get("id")
            if edge.get("rel_type") == "EMPLOYS" and technique_id:
                profile["techniques"].add(technique_id)

        return profile

    def process_single_relationship(self, source_id: str, target_id: str | None = None) -> List[Relationship] | None:
        """
        Calculates mathematical metrics, formats structural prompt vectors, and triggers 
        the structured LLM completion program once per unique pair to populate bidirectional links.
        """
        if self.llm is None:
            raise ValueError("An LLM instance must be provided to run process_single_relationship.")

        _, case_study_source_props = self.get_context_from_entity(source_id)
        _, case_study_target_props = self.get_context_from_entity(target_id)

        if not case_study_source_props or not case_study_target_props:
            return None

        analysis = self.similarity_calculations.compute_case_study_similarity(case_study_source_props, case_study_target_props)
        similarity_score = analysis["final_score"]

        prompt_template = self.prompt_template
        if not self.include_reasoning:
            prompt_template = prompt_template.replace(
                ',\n            "reasoning": "Brief technical sentence linking back to evidence elements found in the graph context topology."',
                ''
            ).replace(
                ',\n    "reasoning": "High-level threat intelligence logical tracking explaining why these two specific attack histories cluster together."',
                ''
            )

        program = LLMTextCompletionProgram.from_defaults(
            output_cls=CaseStudySimilarityResponseSchema,
            prompt_template_str=prompt_template,
            llm=self.llm,
            verbose=False
        )

        case_study_context_source = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.SOURCE,
            entity_id=source_id,
            entity_type=EntityType.CASE_STUDY
        )
        case_study_context_target = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.TARGET,
            entity_id=target_id,
            entity_type=EntityType.CASE_STUDY
        )
        combined_context = f"{case_study_context_source}\n{case_study_context_target}"

        for attempt in range(3):
            try:
                llm_output: CaseStudySimilarityResponseSchema = program(
                    graph_context=combined_context,
                    final_score=similarity_score,
                    name_1=case_study_source_props.get("name", "Unknown Source"), id_1=source_id,
                    name_2=case_study_target_props.get("name", "Unknown Target"), id_2=target_id,
                    exact_techniques=str(analysis.get("exact_shared_techniques", [])),
                    soft_matches=str(analysis.get("soft_matched_pairs", []))
                )

                if not llm_output.entity_relationships:
                    return None

                target_rel = llm_output.entity_relationships[0]
                description_text = target_rel.description.strip()

                return [
                    Relationship(
                        source=source_id,
                        target=target_id,
                        relationship_type=RelationshipType.IS_SIMILAR_TO,
                        description=description_text,
                        similar_to_coef=similarity_score,
                        reasoning=target_rel.reasoning if self.include_reasoning else None,
                    ),
                    Relationship(
                        source=target_id,
                        target=source_id,
                        relationship_type=RelationshipType.IS_SIMILAR_TO,
                        description=description_text,
                        similar_to_coef=similarity_score,
                        reasoning=target_rel.reasoning if self.include_reasoning else None,
                    )
                ]
            except Exception as e:
                if "429" in str(e):
                    time.sleep(10)
                else:
                    raise e
        return None

    def process_all_relationships(self) -> List[Relationship]:
        """
        Deduplicates matrix combinations globally using lexical constraints to enforce zero task repetition.
        """
        min_threshold = 0.40
        top_n = 5

        find_all_query = "MATCH (c:CaseStudy) RETURN c.id AS case_id"
        records, _, _ = self.graph_store.client.execute_query(find_all_query)
        
        case_study_ids = sorted([record["case_id"] for record in records])
        total_case_studies = len(case_study_ids)
        
        candidates = []

        # Compare each pair once; the insert step creates both directions later.
        for source_index in range(total_case_studies):
            for target_index in range(source_index + 1, total_case_studies):
                case_study_source_id = case_study_ids[source_index]
                case_study_target_id = case_study_ids[target_index]
                
                try:
                    _, case_study_source_props = self.get_context_from_entity(case_study_source_id)
                    _, case_study_target_props = self.get_context_from_entity(case_study_target_id)
                    
                    if not case_study_source_props or not case_study_target_props:
                        continue

                    score_meta = self.similarity_calculations.compute_case_study_similarity(
                        case_study_source_props, 
                        case_study_target_props
                    )
                    similarity_score = score_meta["final_score"]
                    
                    if similarity_score >= min_threshold:
                        candidates.append((case_study_source_id, case_study_target_id, similarity_score))
                except Exception:
                    continue

        candidates.sort(key=lambda x: x[2], reverse=True)
        top_candidates = candidates[:top_n]

        results: List[Relationship] = []
        if not top_candidates:
            print(f"No global case study pairs met the minimum similarity threshold of {min_threshold}.")
            return results

        print(f"Filtered down to top {len(top_candidates)} high-confidence deduplicated case study pairs.")
        
        for index, (case_study_source_id, case_study_target_id, similarity_score) in enumerate(top_candidates, start=1):
            print(f"[{index}/{len(top_candidates)}] Processing Symmetric Case Edge: ({case_study_source_id} <=> {case_study_target_id}) | Score: {similarity_score}")
            try:
                bidirectional_edges = self.process_single_relationship(
                    source_id=case_study_source_id, 
                    target_id=case_study_target_id
                )
                if bidirectional_edges:
                    results.extend(bidirectional_edges)
            except Exception as err:
                print(f"  Failed generating case study similarity description for unique pair ({case_study_source_id}, {case_study_target_id}): {err}")
            time.sleep(1.5)

        return results


if __name__ == "__main__":
    graph_store, llm = get_connections()
    calculator = CaseStudySimilarityCalculator(graph_store, llm)
    
    try:
        similarity_relationships = calculator.process_all_relationships()
        print(f"Successfully generated {len(similarity_relationships)} directional graph edges.")
    except Exception as error:
        print(f"Runtime Execution Error: {error}")
