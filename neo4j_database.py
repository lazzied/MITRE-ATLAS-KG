
import os
from typing import Any, Union
from dotenv import load_dotenv
from neo4j import GraphDatabase
from atlas.enums import AtlasRelationshipType
from atlas.schemas import AtlasRelationship, CaseStudy, Mitigation, Tactic, Technique
from scripts.atlas_entities import AtlasPydanticTransformer
from scripts.derived_entities import (

    transform_lifecycle_phase, 
    transform_platform
)
from scripts.new_entities import (
    transform_attack_phase,
    transform_model_component,
    transform_security_objective,
)
from scripts.schemas import LifeCyclePhase, Platform, Relationship, RelationshipType
from scripts.schemas import AttackPhase, ModelComponent, SecurityObjective



class Neo4jInserter:
    TRANSFORM_MAP = {
        Tactic: AtlasPydanticTransformer.transform_tactic,
        Mitigation: AtlasPydanticTransformer.transform_mitigation,
        Technique: AtlasPydanticTransformer.transform_technique,
        CaseStudy: AtlasPydanticTransformer.transform_case_study,
        LifeCyclePhase: transform_lifecycle_phase,
        Platform: transform_platform,
        AttackPhase: transform_attack_phase,
        ModelComponent: transform_model_component,
        SecurityObjective: transform_security_objective,
    }

    RELATIONSHIP_MAPPER = {
        AtlasRelationshipType.ACHIEVES: "ACHIEVES",
        AtlasRelationshipType.SPECIALIZES: "SUBTECHNIQUE_OF",
        AtlasRelationshipType.MITIGATES: "MITIGATES",
        AtlasRelationshipType.EMPLOYS: "DEMONSTRATES",
        RelationshipType.ACHIEVES: "ACHIEVES",
        RelationshipType.SPECIALIZES: "SUBTECHNIQUE_OF",
        RelationshipType.MITIGATES: "MITIGATES",
        RelationshipType.DEMONSTRATES: "DEMONSTRATES",
        RelationshipType.APPLIES_TO_PLATFORM: "APPLIES_TO_PLATFORM",
        RelationshipType.APPLIES_IN_PHASE: "APPLIES_IN_PHASE",
        RelationshipType.HAS_ACCESS_TO: "HAS_ACCESS_TO",
        RelationshipType.ALTERS: "ALTERS",
        RelationshipType.HAS_SIMILAR_TECHNIQUES_TO: "HAS_SIMILAR_TECHNIQUES_TO",
        RelationshipType.OCCURS_AT: "OCCURS_AT",
        RelationshipType.VIOLATES: "VIOLATES",
    }

    def __init__(self, driver):
        self.driver = driver

    def execute(self, query: str, **parameters) -> None:
        """
        Private central runner to handle session boundaries cleanly 
        without repeating context block syntax.
        """
        with self.driver.session() as session:
            session.run(query, **parameters)

    def insert_entity(self, entity: Any) -> None:
        label = type(entity).__name__
        data = self.TRANSFORM_MAP[type(entity)](entity)

        entity_id = data.pop("id")
        
        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
        self.execute(query, id=entity_id, props=data)

    def insert_relationship(self, relationship: Union[AtlasRelationship, Relationship]) -> None:
        """
        Unified relationship insertion engine. Handles both standard matrix relationships 
        and derived platform/lifecycle-phase relationships under a single routine.
        """
        # Case A: Handle custom derived relationship dataclass object
        if isinstance(relationship, Relationship):
            source_id = (
                relationship.source.value
                if hasattr(relationship.source, 'value')
                else relationship.source
            )
            # Safe extraction handling for enum values (PlatformID / LifecyclePhaseID)
            target_id = (
                relationship.target.value 
                if hasattr(relationship.target, 'value') 
                else relationship.target
            )
            rel_type = relationship.relationship_type
            
            props = {}
            if relationship.description:
                props["description"] = relationship.description
            if relationship.mitigation_type:
                props["mitigation_type"] = [
                    mitigation_type.value
                    for mitigation_type in relationship.mitigation_type
                ]
            if relationship.required is not None:
                props["required"] = relationship.required

        # Case B: Handle standard core AtlasRelationship components
        else:
            data = AtlasPydanticTransformer.transform_relationship(relationship)
            source_id = data.pop("source")
            target_id = data.pop("target")
            rel_type = data.pop("relationship_type")

            if rel_type == AtlasRelationshipType.SEQUENCES:
                return

            props = {k: v for k, v in data.items() if v is not None and v != []}

        # Resolve uniform Cypher execution layout
        mapped_type = self.RELATIONSHIP_MAPPER[rel_type]
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{mapped_type}]->(target)
        SET r += $props
        """
        self.execute(query, source_id=source_id, target_id=target_id, props=props)


class Neo4jClient:
    def __init__(self):
        load_dotenv()
        self.uri = os.getenv("NEO4J_URI")
        self.auth = (
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD"),
        )
        self.driver = None

    def connect(self) -> None:
        self.driver = GraphDatabase.driver(self.uri, auth=self.auth)
        self._verify_connectivity()
        print("Connected to Neo4j database engine safely.")

    def _verify_connectivity(self) -> None:
        with self.driver.session() as session:
            session.run("RETURN 1")

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            print("Neo4j database engine connections dropped cleanly.")
