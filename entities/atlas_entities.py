from atlas.schemas import AtlasRelationship, AtlasRelationshipType, Tactic, Mitigation, Technique, CaseStudy
import yaml
from atlas.schemas import AtlasExport
# this script is used to convert the pydantic objects from the atlas data to 
#entities and relationships in the neo4j graph database


# we first need to define the entities:
# tactic/ mitigation/ technique/ use case and their properties
# define the relationships between them:




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
    

