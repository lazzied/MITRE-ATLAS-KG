import time
from typing import List
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.context_queries import TECHNIQUE_CONTEXT_QUERY
from scripts.classifiers.initialization import get_connections
from scripts.classifiers.interface import BaseRelationshipClassifier
from scripts.classifiers.llm_schemas import TechniqueSimilarityResponseSchema
from scripts.classifiers.prompts import TECHNIQUE_SIMILARITY_PROMPT
from scripts.classifiers.similarity_classifiers.similarity_calculations import TechniqueSimilarityCalculations
from scripts.schemas import EntityBooleanType, EntityType, Relationship, RelationshipType


class TechniqueSimilarityCalculator(BaseRelationshipClassifier):
    """
    Finds similar ATLAS techniques, then asks the LLM to write the explanation for each matched pair.
    """
    def __init__(self, graph_store, llm):
        super().__init__(graph_store, llm, context_cypher_read=TECHNIQUE_CONTEXT_QUERY)
        self.prompt_template = TECHNIQUE_SIMILARITY_PROMPT   
        
        self.similarity_math = TechniqueSimilarityCalculations()

    def get_context_from_entity(self, entity_id: str):
        topology, technique_properties = super().get_context_from_entity(entity_id)
        if not technique_properties:
            return topology, {}
        return topology, self._build_technique_similarity_profile(entity_id, topology, technique_properties)

    def _build_technique_similarity_profile(self, technique_id: str, topology, technique_properties):
        profile = dict(technique_properties)
        profile["tech_id"] = profile.get("id", technique_id)
        profile["alters_set"] = set()
        profile["access_set"] = set()
        profile["occurs_at_set"] = set()
        profile["achieves_set"] = set()
        profile["parent_id"] = None

        # The math layer compares sets, so convert graph edges into small comparable groups.
        for edge in topology:
            relationship_type = edge.get("rel_type")
            target_properties = edge.get("target_props", {})
            target_id = target_properties.get("id")
            if not relationship_type or not target_id:
                continue

            if relationship_type == "ALTERS":
                profile["alters_set"].add(target_id)
            elif relationship_type == "HAS_ACCESS_TO":
                profile["access_set"].add(target_id)
            elif relationship_type == "OCCURS_AT":
                profile["occurs_at_set"].add(target_id)
            elif relationship_type == "ACHIEVES":
                profile["achieves_set"].add(target_id)
            elif relationship_type == "SUBTECHNIQUE_OF":
                profile["parent_id"] = target_id

        return profile

    def process_single_relationship(self, source_id: str, target_id: str | None = None) -> List[Relationship] | None:
        """
        Runs an LLM call once for a unique pair and returns a list containing both directional edges.
        """
        _, source_technique_profile = self.get_context_from_entity(source_id)
        _, target_technique_profile = self.get_context_from_entity(target_id)
        
        if not source_technique_profile or not target_technique_profile:
            return None

        similarity_analysis = self.similarity_math.compute_technique_similarity(
            source_technique_profile,
            target_technique_profile
        )
        similarity_score = similarity_analysis["final_score"]

        program = LLMTextCompletionProgram.from_defaults(
            output_cls=TechniqueSimilarityResponseSchema,
            prompt_template_str=self.prompt_template,
            llm=self.llm,
            verbose=False
        )

        source_technique_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.SOURCE,
            entity_id=source_id,
            entity_type=EntityType.TECHNIQUE
        )
        
        target_technique_context = self.build_context_prompt_from_entity(
            entity_boolean_type=EntityBooleanType.TARGET,
            entity_id=target_id,
            entity_type=EntityType.TECHNIQUE
        )
        
        combined_context = f"{source_technique_context}\n{target_technique_context}"

        for attempt in range(3):
            try:
                llm_output: TechniqueSimilarityResponseSchema = program(
                    graph_context=combined_context,
                    technique_id_1=source_id,
                    technique_id_2=target_id,
                    final_score=similarity_score
                )

                target_rel = llm_output.entity_relationships[0]
                description_text = target_rel.description.strip()

                return [
                    Relationship(
                        source=source_id,
                        target=target_id,
                        relationship_type=RelationshipType.IS_SIMILAR_TO,
                        description=description_text,
                        similar_to_coef=similarity_score
                    ),
                    Relationship(
                        source=target_id,
                        target=source_id,
                        relationship_type=RelationshipType.IS_SIMILAR_TO,
                        description=description_text,
                        similar_to_coef=similarity_score
                    )
                ]

            except Exception as e:
                if "429" in str(e):
                    print(f"Rate limit hit. Retrying in a bit... (Attempt {attempt+1}/3)")
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

        find_all_query = "MATCH (t:Technique) RETURN t.id AS tech_id"
        records, _, _ = self.graph_store.client.execute_query(find_all_query)
        
        technique_ids = sorted([record["tech_id"] for record in records])
        total_techniques = len(technique_ids)
        
        candidates = []

        # Compare each pair once; the insert step creates both directions later.
        for source_index in range(total_techniques):
            for target_index in range(source_index + 1, total_techniques):
                source_technique_id = technique_ids[source_index]
                target_technique_id = technique_ids[target_index]
                
                try:
                    _, source_profile = self.get_context_from_entity(source_technique_id)
                    _, target_profile = self.get_context_from_entity(target_technique_id)
                    
                    if not source_profile or not target_profile:
                        continue

                    score_meta = self.similarity_math.compute_technique_similarity(source_profile, target_profile)
                    similarity_score = score_meta["final_score"]
                    
                    if similarity_score >= min_threshold:
                        candidates.append((source_technique_id, target_technique_id, similarity_score))
                except Exception:
                    continue

        candidates.sort(key=lambda x: x[2], reverse=True)
        top_candidates = candidates[:top_n]

        results: List[Relationship] = []
        if not top_candidates:
            print(f"No global technique pairs met the minimum similarity threshold of {min_threshold}.")
            return results

        print(f"Filtered down to top {len(top_candidates)} high-confidence deduplicated similarity pairs.")
        
        for index, (source_technique_id, target_technique_id, similarity_score) in enumerate(top_candidates, start=1):
            
            print(f"[{index}/{len(top_candidates)}] Processing Symmetric Edge: ({source_technique_id} <=> {target_technique_id}) | Score: {similarity_score}")
            
            try:
                
                bidirectional_edges = self.process_single_relationship(
                    source_id=source_technique_id,
                    target_id=target_technique_id
                )
                
                if bidirectional_edges:
                    results.extend(bidirectional_edges)
                    
            except Exception as err:
                print(f"  Failed generating similarity description for unique pair ({source_technique_id}, {target_technique_id}): {err}")
            time.sleep(1.5)

        return results


if __name__ == "__main__":
    graph_store, llm = get_connections()
    calculator = TechniqueSimilarityCalculator(graph_store, llm)
    
    try:
        similarity_relationships = calculator.process_all_relationships()
        print(f"Successfully generated {len(similarity_relationships)} total directional graph edges.")
    except Exception as error:
        print(f"Runtime Execution Error: {error}")
