import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATLAS_PATH = ROOT / "atlas-data"

print("ADDING PATH:", ATLAS_PATH)  # debug line

sys.path.insert(0, str(ATLAS_PATH))
from atlas.schemas import AtlasRelationship, AtlasRelationshipType, Tactic, Mitigation, Technique, CaseStudy
import yaml
from atlas.schemas import AtlasExport
# this script is used to convert the pydantic objects from the atlas data to 
#entities and relationships in the neo4j graph database


# we first need to define the entities:
# tactic/ mitigation/ technique/ use case and their properties
# define the relationships between them:
from neo4j import GraphDatabase

import os
from dotenv import load_dotenv



class AtlasPydanticTransformer:
    # this class is used to transform oydantic objects to dicts that can be inserted to neo4j
    @staticmethod
    def transform_tactic(tactic: Tactic):
        #this takes in a tactic object and transforms it into a neo4j node structure that's ready to be inserted
        return {
            "id": tactic.id,
            "name": tactic.name,
            "description": tactic.description,
            "references": [str(r.url) for r in tactic.references],
            "attack_reference": tactic.attack_reference.id if tactic.attack_reference else None,
        }

    @staticmethod
    def transform_mitigation(mitigation: Mitigation):
        #this takes in a mitigation object and transforms it into a neo4j node structure that's ready to be inserted
        return {
            "id": mitigation.id,
            "name": mitigation.name,
            "description": mitigation.description,
            "references": [str(r.url) for r in mitigation.references],
            "attack_reference": mitigation.attack_reference.id if mitigation.attack_reference else None,
            "lifecycle_phases": [p.value for p in mitigation.lifecycle_phases],
            "categories": [c.value for c in mitigation.categories],
        }

    @staticmethod
    def transform_technique(technique: Technique):
        #this takes in a technique object and transforms it into a neo4j node structure that's ready to be inserted
        
        return {
            "id": technique.id,
            "name": technique.name,
            "description": technique.description,
            "references": [str(r.url) for r in technique.references],
            "attack_reference": technique.attack_reference.id if technique.attack_reference else None,
            "maturity": technique.maturity.value,
            "platforms": [p.value for p in technique.platforms],
        }
        
    @staticmethod
    def transform_case_study(case_study: CaseStudy):
        #this takes in a use case object and transforms it into a neo4j node structure that's ready to be inserted
        
        return {
            "id": case_study.id,
            "name": case_study.name,
            "description": case_study.description,
            "references": [str(r.url) for r in case_study.references],
            "type": case_study.type.value,
            "actor": case_study.actor,
            "target": case_study.target,
            "reporter": case_study.reporter,
            "date": case_study.date.isoformat(),
            "date_granularity": case_study.date_granularity.value,
        }
        
    @staticmethod
    def transform_relationship(relationship: AtlasRelationship):
        return {
            "source": relationship.source,
            "target": relationship.target,
            "relationship_type": relationship.relationship_type,
            "description": relationship.description,
            "tactic": relationship.tactic,
            "step_id": relationship.step_id,
            "leads_to": [str(s) for s in relationship.leads_to] if relationship.leads_to else None,
            "position": relationship.position,
        }   
    

class Neo4jInserter:
    
    TRANSFORM_MAP = {
    Tactic: AtlasPydanticTransformer.transform_tactic,
    Mitigation: AtlasPydanticTransformer.transform_mitigation,
    Technique: AtlasPydanticTransformer.transform_technique,
    CaseStudy: AtlasPydanticTransformer.transform_case_study,
}
    RELATIONSHIP_MAPPER = {
        
    AtlasRelationshipType.ACHIEVES: "ACHIEVES",
    AtlasRelationshipType.SPECIALIZES: "SUBTECHNIQUE_OF",
    AtlasRelationshipType.MITIGATES: "MITIGATES",
    AtlasRelationshipType.EMPLOYS: "DEMONSTRATES",
    
}
    def __init__(self, driver):
        self.driver = driver
        
    def insert_entity(self, entity):
        #this takes in a node structure and inserts it into the neo4j graph database
        label = type(entity).__name__                 #  "Tactic", "Technique"
        data = self.TRANSFORM_MAP[type(entity)](entity)      # convert pydantic model to a  dict

        entity_id = data.pop("id")                    # remove id from dict stored separately
        props = data                                # remaining attrs become node properties

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
            
            

if __name__ == "__main__":
    load_dotenv()

    URI = os.getenv("NEO4J_URI")
    AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

    driver = GraphDatabase.driver(URI, auth=AUTH)

    # verify connection
    with driver.session() as session:
        session.run("RETURN 1")

    print("Connected to Neo4j")

    path = Path("atlas-data/dist/v6/ATLAS-2026.05.yaml")

    with path.open("r") as f:
        raw = yaml.safe_load(f)

    atlas_data = AtlasExport.model_validate(raw)

    inserter = Neo4jInserter(driver)

    counts = {"Tactic": 0, "Mitigation": 0, "Technique": 0, "CaseStudy": 0, "Relationship": 0}
    errors = []

    for tactic in atlas_data.tactics.values():
        try:
            inserter.insert_entity(tactic)
            counts["Tactic"] += 1
        except Exception as e:
            errors.append(f"Tactic {tactic.id}: {e}")

    for mitigation in atlas_data.mitigations.values():
        try:
            inserter.insert_entity(mitigation)
            counts["Mitigation"] += 1
        except Exception as e:
            errors.append(f"Mitigation {mitigation.id}: {e}")

    for technique in atlas_data.techniques.values():
        try:
            inserter.insert_entity(technique)
            counts["Technique"] += 1
        except Exception as e:
            errors.append(f"Technique {technique.id}: {e}")

    for case_study in atlas_data.case_studies.values():
        try:
            inserter.insert_entity(case_study)
            counts["CaseStudy"] += 1
        except Exception as e:
            errors.append(f"CaseStudy {case_study.id}: {e}")

    for source_id, rel_by_type in atlas_data.relationships.items():
        for rel_type, rel_list in rel_by_type.items():
            for relationship in rel_list:
                try:
                    inserter.insert_relationship(relationship)
                    counts["Relationship"] += 1
                except Exception as e:
                    errors.append(f"Relationship {relationship.source}->{relationship.target} ({rel_type}): {e}")

    print(f"\nInserted:")
    print(f"  Tactics:       {counts['Tactic']}")
    print(f"  Mitigations:   {counts['Mitigation']}")
    print(f"  Techniques:    {counts['Technique']}")
    print(f"  Case Studies:  {counts['CaseStudy']}")
    print(f"  Relationships: {counts['Relationship']}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for err in errors:
            print(f"  [ERROR] {err}")
    else:
        print("\nDone inserting data into Neo4j")

    driver.close()
        
    
    
    # now this data will need to be inserted in the neo4js