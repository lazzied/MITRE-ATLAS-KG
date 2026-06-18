
import os
from pathlib import Path
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
        AtlasRelationshipType.EMPLOYS: "EMPLOYS",
        RelationshipType.SPECIALIZES: "SUBTECHNIQUE_OF",
        RelationshipType.MITIGATES: "MITIGATES",
        RelationshipType.EMPLOYS: "EMPLOYS",
        RelationshipType.APPLIES_TO_PLATFORM: "APPLIES_TO_PLATFORM",
        RelationshipType.APPLIES_IN_PHASE: "APPLIES_IN_PHASE",
        RelationshipType.HAS_ACCESS_TO: "HAS_ACCESS_TO",
        RelationshipType.ALTERS: "ALTERS",
        RelationshipType.IS_SIMILAR_TO: "IS_SIMILAR_TO",
        RelationshipType.OCCURS_AT: "OCCURS_AT",
        RelationshipType.VIOLATES: "VIOLATES",
    }
    NODE_LABELS = tuple(entity_cls.__name__ for entity_cls in TRANSFORM_MAP)
    NAME_INDEX_LABELS = NODE_LABELS

    def __init__(self, driver):
        self.driver = driver

    def execute(self, query: str, **parameters) -> None:
        """
        Private central runner to handle session boundaries cleanly 
        without repeating context block syntax.
        """
        with self.driver.session() as session:
            session.run(query, **parameters).consume()

    def ensure_schema(self) -> None:
        """
        Creates conservative lookup constraints and indexes for stable graph ingestion.
        """
        for label in self.NODE_LABELS:
            constraint_name = f"{label.lower()}_id_unique"
            query = f"""
            CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
            FOR (n:{label}) REQUIRE n.id IS UNIQUE
            """
            self.execute(query)

        for label in self.NAME_INDEX_LABELS:
            index_name = f"{label.lower()}_name_index"
            query = f"""
            CREATE INDEX {index_name} IF NOT EXISTS
            FOR (n:{label}) ON (n.name)
            """
            self.execute(query)

    def insert_entity(self, entity: Any) -> None:
        label = type(entity).__name__
        data = self.TRANSFORM_MAP[type(entity)](entity)

        entity_id = data.pop("id")
        
        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
        self.execute(query, id=entity_id, props=data)

    def _get_relationship_parts(self, relationship: Union[AtlasRelationship, Relationship]):
        """
        Converts both project and ATLAS relationship objects into uniform write parts.
        """
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
            if relationship.similar_to_coef is not None:
                props["similar_to_coef"] = relationship.similar_to_coef
            if relationship.reasoning:
                props["reasoning"] = relationship.reasoning

        else:
            data = AtlasPydanticTransformer.transform_relationship(relationship)
            source_id = data.pop("source")
            target_id = data.pop("target")
            rel_type = data.pop("relationship_type")

            if rel_type == AtlasRelationshipType.SEQUENCES:
                return None

            props = {k: v for k, v in data.items() if v is not None and v != []}

        mapped_type = self.RELATIONSHIP_MAPPER[rel_type]
        return source_id, target_id, mapped_type, props

    def relationship_exists(self, relationship: Union[AtlasRelationship, Relationship]) -> bool:
        parts = self._get_relationship_parts(relationship)
        if parts is None:
            return True

        source_id, target_id, mapped_type, _ = parts
        query = f"""
        MATCH (source {{id: $source_id}})-[r:{mapped_type}]->(target {{id: $target_id}})
        RETURN count(r) AS rel_count
        """
        with self.driver.session() as session:
            record = session.run(
                query,
                source_id=source_id,
                target_id=target_id,
            ).single()

        return bool(record and record["rel_count"] > 0)

    def _verify_relationship_endpoints(self, source_id: str, target_id: str, mapped_type: str) -> None:
        query = """
        OPTIONAL MATCH (source {id: $source_id})
        OPTIONAL MATCH (target {id: $target_id})
        RETURN count(DISTINCT source) AS source_count,
               count(DISTINCT target) AS target_count
        """
        with self.driver.session() as session:
            record = session.run(
                query,
                source_id=source_id,
                target_id=target_id,
            ).single()

        source_count = record["source_count"] if record else 0
        target_count = record["target_count"] if record else 0

        if source_count == 0 or target_count == 0:
            missing = []
            if source_count == 0:
                missing.append(f"source id '{source_id}'")
            if target_count == 0:
                missing.append(f"target id '{target_id}'")
            raise RuntimeError(
                f"Neo4j write failed for {mapped_type}: missing {', '.join(missing)}."
            )

    def insert_relationship(self, relationship: Union[AtlasRelationship, Relationship]) -> bool:
        """
        Unified relationship insertion engine. Returns True only after Neo4j confirms
        a new relationship exists. Existing relationships are skipped.
        """
        parts = self._get_relationship_parts(relationship)
        if parts is None:
            return False

        source_id, target_id, mapped_type, props = parts

        if self.relationship_exists(relationship):
            return False

        self._verify_relationship_endpoints(source_id, target_id, mapped_type)

        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{mapped_type}]->(target)
        SET r += $props
        """
        with self.driver.session() as session:
            summary = session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                props=props,
            ).consume()

        if summary.counters.relationships_created < 1 and not self.relationship_exists(relationship):
            raise RuntimeError(
                f"Neo4j write failed for {mapped_type}: relationship was not persisted."
            )

        return True


class Neo4jClient:
    def __init__(self):
        env_path = Path(__file__).resolve().parent / ".env"
        load_dotenv(dotenv_path=env_path)
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
