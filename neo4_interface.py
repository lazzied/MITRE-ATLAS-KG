import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
import yaml
from atlas.enums import AtlasRelationshipType
from atlas.schemas import AtlasExport, AtlasRelationship, CaseStudy, Mitigation, Tactic, Technique
from scripts.derived_entities import generate_life_cycle_phase_dataclasses, generate_life_cycle_phase_relationship, generate_platform_dataclasses, generate_platform_relationship, transform_lifecycle_phase, transform_platform
from scripts.pydantic_converter import AtlasPydanticTransformer
from scripts.schemas import LifeCyclePhase, Platform, Relationship, RelationshipType


class Neo4jInserter:
    TRANSFORM_MAP = {
        Tactic: AtlasPydanticTransformer.transform_tactic,
        Mitigation: AtlasPydanticTransformer.transform_mitigation,
        Technique: AtlasPydanticTransformer.transform_technique,
        CaseStudy: AtlasPydanticTransformer.transform_case_study,
        LifeCyclePhase: transform_lifecycle_phase,
        Platform: transform_platform,
    }

    RELATIONSHIP_MAPPER = {
        AtlasRelationshipType.ACHIEVES: "ACHIEVES",
        AtlasRelationshipType.SPECIALIZES: "SUBTECHNIQUE_OF",
        AtlasRelationshipType.MITIGATES: "MITIGATES",
        AtlasRelationshipType.EMPLOYS: "DEMONSTRATES",
        RelationshipType.APPLIES_TO_PLATFORM: "APPLIES_TO_PLATFORM",
        RelationshipType.APPLIES_IN_PHASE: "APPLIES_IN_PHASE",
    }

    def __init__(self, driver):
        self.driver = driver

    def insert_entity(self, entity):
        label = type(entity).__name__
        data = self.TRANSFORM_MAP[type(entity)](entity)

        entity_id = data.pop("id")
        props = data

        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"

        with self.driver.session() as session:
            session.run(query, id=entity_id, props=props)

    def insert_relationship(self, relationship: AtlasRelationship):
        data = AtlasPydanticTransformer.transform_relationship(relationship)

        source_id = data.pop("source")
        target_id = data.pop("target")
        rel_type = data.pop("relationship_type")

        if rel_type == AtlasRelationshipType.SEQUENCES:
            return

        props = {k: v for k, v in data.items() if v is not None and v != []}

        query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            MERGE (source)-[r:{self.RELATIONSHIP_MAPPER[rel_type]}]->(target)
            SET r += $props
        """

        with self.driver.session() as session:
            session.run(query, source_id=source_id, target_id=target_id, props=props)

    def insert_derived_relationship(self, relationship: Relationship):
        rel_type = relationship.relationship_type
        neo4j_type = self.RELATIONSHIP_MAPPER[rel_type]

        props = {}
        if relationship.description:
            props["description"] = relationship.description

        query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            MERGE (source)-[r:{neo4j_type}]->(target)
            SET r += $props
        """

        with self.driver.session() as session:
            session.run(
                query,
                source_id=relationship.source,
                target_id=relationship.target.value,  # PlatformID / LifecyclePhaseID enum
                props=props,
            )

    def insert_atlas_entities(self, atlas_data):
        for tactic in atlas_data.tactics.values():
            self.insert_entity(tactic)

        for mitigation in atlas_data.mitigations.values():
            self.insert_entity(mitigation)

        for technique in atlas_data.techniques.values():
            self.insert_entity(technique)

        for case_study in atlas_data.case_studies.values():
            self.insert_entity(case_study)

    def insert_atlas_relationships(self, atlas_data):
        for source_id, rel_by_type in atlas_data.relationships.items():
            for rel_type, rel_list in rel_by_type.items():
                for relationship in rel_list:
                    self.insert_relationship(relationship)

    def insert_derived_entities(self,life_cycle_phase_objects, platform_objects):
        for phase in life_cycle_phase_objects:
            self.insert_entity(phase)

        for platform in platform_objects:
            self.insert_entity(platform)

    def insert_derived_relationships(self, atlas_data):
        for technique in atlas_data.techniques.values():
            for rel in generate_platform_relationship(technique):
                self.insert_derived_relationship(rel)

        for mitigation in atlas_data.mitigations.values():
            for rel in generate_life_cycle_phase_relationship(mitigation):
                self.insert_derived_relationship(rel)

   
class Neo4jClient:
    def __init__(self):
        load_dotenv()

        self.uri = os.getenv("NEO4J_URI")
        self.auth = (
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD"),
        )

        self.driver = None

    def connect(self):
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=self.auth,
        )

        # Verify connection
        with self.driver.session() as session:
            session.run("RETURN 1")

        print("Connected to Neo4j")

    def close(self):
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed")

if __name__ == "__main__":
    client = Neo4jClient()
    client.connect()
    
    path = Path("atlas-data/dist/v6/ATLAS-2026.05.yaml")
    with path.open("r") as f:
        raw = yaml.safe_load(f)

    atlas_data = AtlasExport.model_validate(raw)
    inserter = Neo4jInserter(client.driver)


    client.close()