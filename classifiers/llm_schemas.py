from typing import Dict, List
from pydantic import BaseModel, Field
from atlas.schemas import TechniqueId
from scripts.schemas import AttackPhaseID, MitigationCategoryType, ModelComponentID, SecurityObjectiveID


class ViolatesRelationshipSchema(BaseModel):
    """
    Represents a single discovered violation link pointing to an impacted security objective.
    """
    source_entity: TechniqueId = Field(
        description="The source ATLAS Technique identifier from which this structural violation originates."
    )
    target_entity: SecurityObjectiveID = Field(
        description="The target Security Objective node that this technique violates."
    )
    descriptions: List[str] = Field(
        description="A list containing one or more exact predefined description strings corresponding to this objective type."
    )
    reasoning: str = Field(
        description="Clear, text-grounded cybersecurity reasoning detailing how the technique achieves these specific impacts."
    )


class ViolatesResponseSchema(BaseModel):
    """
    The full payload structure returned from Mistral containing all mapped security objective entity_relationships.
    """
    entity_relationships: List[ViolatesRelationshipSchema] = Field(
        description="List of valid VIOLATES relationships directly supported by graph context. Omit objectives with no active violation."
    )
    reasoning: str = Field(
        description="High-level cognitive logic tracking the overall evaluation process across tactics and case studies."
    )


class OccursAtRelationshipSchema(BaseModel):
    """
    Represents a single discovered lifecycle orientation link pointing to an attack phase.
    """
    source_entity: TechniqueId = Field(
        description="The source ATLAS Technique identifier from which this operational relationship originates."
    )
    target_entity: AttackPhaseID = Field(
        description="The specific Attack Phase node where the technique executes (training or inference)."
    )
    description: str = Field(
        description="A clear, structural architectural justification explaining why this technique targets this specific lifecycle node."
    )
    reasoning: str = Field(
        description="A brief sentence connecting the technique description or case study lifecycle details directly to this phase."
    )

class OccursAtResponseSchema(BaseModel):
    """
    The full payload structure returned from Mistral containing all discovered operational entity_relationships.
    """
    entity_relationships: List[OccursAtRelationshipSchema] = Field(
        description="List of valid OCCURS_AT relationships directly supported by graph data. Must contain at least one phase."
    )
    reasoning: str = Field(
        description="High-level lifecycle logic tracking whether the attack occurs pre-deployment or post-deployment."
    )


class MitigationRelationshipSchema(BaseModel):
    """
    Represents a single discovered mitigation connection mapping into defense categories.
    """
    source_entity: str = Field(
        description="The source identifier (e.g., Mitigation ID or Technique ID) from which this relationship originates."
    )
    target_entity: str = Field(
        description="The target identifier being evaluated under this mitigation coverage constraint."
    )
    categories: List[MitigationCategoryType] = Field(
        description="List of applicable category types for this MITIGATES relationship. Multiple entries are only allowed if there is strong, undeniable evidence."
    )
    
    description: str = Field(
        description="A clear, compiled structural summary explaining the overall mitigation strategy for this link."
    )
    reasoning: str = Field(
        description="Brief sentence connecting the graph context evidence or security control parameters directly to this mapping."
    )


class MitigationResponseSchema(BaseModel):
    """
    The full payload structure returned containing all mapped mitigation entity_relationships.
    """
    entity_relationships: List[MitigationRelationshipSchema] = Field(
        description="List of valid MITIGATES relationships directly supported by graph data. Omit edges with no clear defensive coverage."
    )
    reasoning: str = Field(
        description="Overall high-level cybersecurity logical justification for the classification choices."
    )
    
class HasAccessToRelationshipSchema(BaseModel):
    """
    Represents a single discovered lifecycle orientation link pointing to an access requirement.
    """
    source_entity: TechniqueId = Field(
        description="The source ATLAS Technique identifier from which this access relationship originates."
    )
    target_entity: ModelComponentID = Field(
        description="The specific Model Component node the technique requires or benefits from access to."
    )
    required: bool = Field(
        description="True if the technique absolutely cannot be performed without it. False if it is optional, conditional, or helpful."
    )
    description: str = Field(
        description="A clear, structural architectural justification explaining why this technique targets this specific lifecycle node."
    )
    reasoning: str = Field(
        description="Brief explanation highlighting how the technique uses this component, drawing from descriptions or case study metrics."
    )

class HasAccessToResponseSchema(BaseModel):
    entity_relationships: List[HasAccessToRelationshipSchema] = Field(
        description="List of valid HAS_ACCESS_TO connections. Omit any components that fall under 'No relationship'."
    )
    reasoning: str = Field(
        description="High-level evaluation logic tying the graph context evidence to the final component mappings."
    )


class AltersRelationshipSchema(BaseModel):
    """
    Represents a single discovered modification link pointing to an impacted model component.
    """
    source_entity: TechniqueId = Field(
        description="The source ATLAS Technique identifier from which this access relationship originates."
    )
    
    target_entity: ModelComponentID = Field(
        description="The specific Model Component node that is altered, modified, poisoned, or perturbed by the technique."
    )
    
    description: str = Field(
        description="A clear, structural architectural justification explaining why this technique targets this specific lifecycle node."
    )
    
    reasoning: str = Field(
        description="Brief explanation highlighting how the technique alters or manipulates this component based on graph context data."
    )


class AltersResponseSchema(BaseModel):
    """
    The full payload structure returned from Mistral containing all discovered model target components.
    """
    entity_relationships: List[AltersRelationshipSchema] = Field(
        description="List of valid ALTERS connections. Omit any components that fall under 'Not required' / 'No relationship'."
    )
    reasoning: str = Field(
        description="High-level evaluation logic tying the graph context evidence to the final component alteration mappings."
    )
    
       
class TechniqueSimilarityRelationshipSchema(BaseModel):
    """
    Represents a single discovered similarity link pointing to a functionally related ATLAS Technique.
    """
    source_entity: TechniqueId = Field(
        description="The source ATLAS Technique identifier from which this similarity relationship originates."
    )
    target_entity: TechniqueId = Field(
        description="The target ATLAS Technique identifier that shares functional or structural operational execution steps."
    )
    similarity_coeff: float = Field(
        description="A floating-point metric value indicating the degree of functional overlap between the two techniques."
    )
    description: str = Field(
        description="A clear, structural architectural justification summarizing the shared mechanical overlap between both nodes."
    )
    reasoning: str = Field(
        description="Brief sentence connecting shared model components, visibility prerequisites, or tactics directly to this mapping."
    )


class TechniqueSimilarityResponseSchema(BaseModel):
    """
    The full payload structure returned containing all discovered technique similarity relationships.
    """
    entity_relationships: List[TechniqueSimilarityRelationshipSchema] = Field(
        description="List of valid technique similarity connections supported by shared graph contexts and operational characteristics."
    )
    reasoning: str = Field(
        description="A concise summary explaining why these techniques are functionally similar based on their shared model components, visibility prerequisites, lifecycle phases, and tactics."
    )
    
class CaseStudySimilarityRelationshipSchema(BaseModel):
    """
    Represents a single discovered campaign similarity boundary link pointing to an overlapping Case Study.
    """
    source_entity: str = Field(
        description="The source MITRE ATLAS Case Study identifier from which this campaign relationship originates."
    )
    target_entity: str = Field(
        description="The target MITRE ATLAS Case Study identifier that demonstrates high behavioral or operational crossover."
    )
    similarity_coeff: float = Field(
        description="A floating-point metric value tracking the final blended mathematical matrix similarity score."
    )
    description: str = Field(
        description="A professional, narrative paragraph explaining the behavioral overlap between both case studies using their techniques."
    )
    reasoning: str = Field(
        description="Brief sentence connecting shared adversarial vectors or targeted model pipeline components back to graph telemetry."
    )


class CaseStudySimilarityResponseSchema(BaseModel):
    """
    The full structured payload contract returned from the LLM validating operational campaign crossovers.
    """
    entity_relationships: List[CaseStudySimilarityRelationshipSchema] = Field(
        description="List containing valid case study similarity connections supported by exact intersections and soft matches."
    )
    reasoning: str = Field(
        description="High-level threat intelligence logical tracking explaining why these two specific attack histories cluster together."
    )