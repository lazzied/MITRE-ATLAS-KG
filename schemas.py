# here we define the entities and relationships that we want to store in neo4j, and the properties of each entity and relationship 
from dataclasses import dataclass
from enum import Enum
from atlas.enums import MitigationLifecyclePhasesType, TechniquePlatformType
from atlas.schemas import CaseStudy, Mitigation, Tactic, Technique, AtlasRelationship

    
@dataclass
class AISystem():
    type: TechniquePlatformType
    description: str

@dataclass
class LifecyclePhase():
    type: MitigationLifecyclePhasesType
    description:str 


class ModelComponentType(Enum):
    TRAINING_SAMPLES = "training_samples"
    TRAINING_LABElS = "training_labels"
    TEST_SAMPLES = "test_samples"
    TEST_LABELS = "test_labels"
    WEIGHTS = "weights"
    OUTPUT = "output"
    
@dataclass
class ModelComponent():
    type: ModelComponentType
    description:str


class SecurityObjectiveType(Enum):
    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"


@dataclass
class SecurityObjective():
    type: SecurityObjectiveType
    description:str
    
class AttackPhaseType(Enum):
    INFERENCE = "inference"
    TRAINING = "training"
    
@dataclass
class AttackPhase():
    type: AttackPhaseType
    description:str

class MitigationCategoryType(Enum):
    PREVENTIVE = "preventive"   # this is defensive preparations that reduce the attack surface before any attack
    HARDENING  = "hardening"    # this is during an attack ; reduces attack effectiveness during an attack even if it were to happen
    DETECTIVE  = "detective"    # this is monitoring; identifies attacks or integrity violations


class AtlasRelationshipType(Enum):
    # define the relationship types between the entities (edges in the graph)
    
    ACHIEVES = "achieves" # technique achieves a tactic
    SPECIALIZES = "specializes" #subtechnique specializes a technique
    MITIGATES = "mitigates" #mitigation mitigates a technique
    DEMONSTRATES = "demonstrates" # use case demonstrates  technique # 
    APPLIES_IN_PHASE = "applies_in_phase" # a mitigation applies in a lifecycle phase # example questions: currently under phase X in the developement, what measures should i take to prevent a breach?
    APPLIES_TO_SYSTEM = "applies_to_system" # a mitigation applies to an AI system # my project is using generative AI, what mitigations should i implement? and what techniques should i be aware of?
    HAS_ACCESS_TO = "has_access_to" # a technique to be performed requires access to an AI system component
    ALTERS = "alters" # An attacker uses technique to alter a model component
    HAS_SIMILAR_TECHNIQUES_TO = "similar_techniques_to" # a case study is similar to another case study in terms of techniques used
    OCCURS_AT = "occurs_at" # an attack occurs at a certain phase
    TARGETS = "targets" # a technique targets a certain security objective (confidentiality, integrity, availability)
    
    