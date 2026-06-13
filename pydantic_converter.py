from atlas.schemas import AtlasRelationship, Tactic, Mitigation, Technique, CaseStudy

# this script is used to convert the pydantic objects from the atlas data to 
#entities and relationships in the neo4j graph database


# we first need to define the entities:
# tactic/ mitigation/ technique/ use case and their properties
# define the relationships between them:
from neo4j import GraphDatabase

import os
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

driver = GraphDatabase.driver(URI, auth=AUTH)

# verify connection
with driver.session() as session:
    session.run("RETURN 1")

print("Connected to Neo4j")

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
            "date": case_study.date.isoformat(),
        }
        
    @staticmethod
    def transform_relationship(relationship: AtlasRelationship):
        return {
            "source": relationship.source,
            "target": relationship.target,
            "relationship_type": relationship.relationship_type.value,
            "description": relationship.description,
            "tactic": relationship.tactic,
            "step_id": relationship.step_id,
            "leads_to": relationship.leads_to,
            "position": relationship.position,
        }   
    

class Neo4jInserter:
    
    TRANSFORM_MAP = {
    Tactic: AtlasPydanticTransformer.transform_tactic,
    Mitigation: AtlasPydanticTransformer.transform_mitigation,
    Technique: AtlasPydanticTransformer.transform_technique,
    CaseStudy: AtlasPydanticTransformer.transform_case_study,
}
    def __init__(self, driver):
        self.driver = driver
        
    def insert_node(self, node):
        #this takes in a node structure and inserts it into the neo4j graph database
        label = type(node).__name__                 #  "Tactic", "Technique"
        data = self.TRANSFORM_MAP[type(node)](node)      # convert pydantic model to a  dict

        node_id = data.pop("id")                    # remove id from dict stored separately
        props = data                                # remaining attrs become node properties

        query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"

        with driver.session() as session:
            session.run(query, id=node_id, props=props)
        

def insert_relationship(relationship: AtlasRelationship):
    data = AtlasPydanticTransformer.transform_relationship(relationship)

    source_id = data.pop("source")
    target_id = data.pop("target")
    rel_type = data.pop("relationship_type")

    props = {k: v for k, v in data.items() if v is not None}

    query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $props
    """

    with driver.session() as session:
        session.run(query, source_id=source_id, target_id=target_id, props=props)