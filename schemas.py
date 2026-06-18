# here we define the entities and relationships that we want to store in neo4j, and the properties of each entity and relationship 
from dataclasses import dataclass
from enum import Enum

from pydantic import Field
from atlas.enums import MitigationLifecyclePhasesType, TechniquePlatformType
from atlas.schemas import ASCII_TEXT, CaseStudyId, MitigationId, TacticId, TechniqueId

class PlatformID (Enum):
    PREDICTIVE = "predictive"
    GENERATIVE = "generative"
    AGENTIC = "agentic"
    ENTERPRISE = "enterprise"
     
     
class LifecyclePhaseID (Enum):
    DATA_UNDERSTANDING = "data_understanding"
    DATA_PREPARATION = "data_preparation"
    MODEL_ENGINEERING = "model_engineering"
    MODEL_EVALUATION = "model_evaluation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

class ModelComponentID (Enum):
    TRAINING_SAMPLES = "training_samples"
    TRAINING_LABELS = "training_labels"
    TEST_SAMPLES = "test_samples"
    TEST_LABELS = "test_labels"
    WEIGHTS = "weights"
    OUTPUT = "output"
    
class SecurityObjectiveID (Enum):
    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"
    
class AttackPhaseID (Enum):
    INFERENCE = "inference"
    TRAINING = "training"

@dataclass
class Platform():
    id: PlatformID
    type: TechniquePlatformType
    description: str

@dataclass
class LifeCyclePhase():
    id: LifecyclePhaseID
    type: MitigationLifecyclePhasesType
    description:str 


class ModelComponentType(Enum):
    TRAINING_SAMPLES = "Training samples"
    TRAINING_LABELS = "Training labels"
    TEST_SAMPLES = "Test samples"
    TEST_LABELS = "Test labels"
    WEIGHTS = "Weights"
    OUTPUT = "Output"
    
@dataclass
class ModelComponent():
    id: ModelComponentID
    type: ModelComponentType
    description:str


class SecurityObjectiveType(Enum):
    CONFIDENTIALITY = "confidentiality"
    INTEGRITY = "integrity"
    AVAILABILITY = "availability"


@dataclass
class SecurityObjective():
    id: SecurityObjectiveID
    type: SecurityObjectiveType
    description:str
    
class AttackPhaseType(Enum):
    INFERENCE = "inference"
    TRAINING = "training"
    
@dataclass
class AttackPhase():
    id: AttackPhaseID
    type: AttackPhaseType
    description:str

class MitigationCategoryType(Enum):
    PREVENTIVE = "preventive"   # this is defensive preparations that reduce the attack surface before any attack
    HARDENING  = "hardening"    # this is during an attack ; reduces attack effectiveness during an attack even if it were to happen
    DETECTIVE  = "detective"    # this is monitoring; identifies attacks or integrity violations

class EntityType(Enum):
    ATTACK_PHASE = "attack_phase"
    SECURITY_OBJECTIVE = "security_objective"
    MODEL_COMPONENT = "model_component"
    PLATFORM = "platform"
    LIFECYCLE_PHASE = "lifecycle_phase"
    CASE_STUDY = "case_study"
    TECHNIQUE = "technique"
    MITIGATION = "mitigation"
    TACTIC = "tactic"

class RelationshipType(Enum):
    # define the relationship types between the entities (edges in the graph) an extended version of the ATLAS RELATIONSHIP TYPE
    
    ACHIEVES = "achieves" # technique achieves a tactic
    SPECIALIZES = "specializes" #subtechnique specializes a technique
    MITIGATES = "mitigates" #mitigation mitigates a technique
    EMPLOYS = "employs" # use case employs technique # 
    APPLIES_IN_PHASE = "applies_in_phase" # a mitigation applies in a lifecycle phase # example questions: currently under phase X in the developement, what measures should i take to prevent a breach?
    APPLIES_TO_PLATFORM = "applies_to_platform" # a tachnique applies to an platform # my project is using generative AI,what techniques should i be aware of? 
    HAS_ACCESS_TO = "has_access_to" # a technique to be performed requires access to an model component
    ALTERS = "alters" # An attacker uses technique to alter a model component
    OCCURS_AT = "occurs_at" # an attack occurs at a certain phase
    VIOLATES = "violates" # a technique violates a certain security objective (confidentiality, integrity, availability)
    IS_SIMILAR_TO = "is_similar_to" # a technique is similar to technique
    
ObjectId = (
    TacticId | TechniqueId | MitigationId | CaseStudyId | PlatformID | LifecyclePhaseID | ModelComponentID | SecurityObjectiveID | AttackPhaseID
)

class EntityBooleanType(Enum):
    SOURCE = "source"
    TARGET= "target"


@dataclass
class Relationship(): # this is a simplified relationship class from
    source: ObjectId
    target: ObjectId
    relationship_type: RelationshipType
    description: str | None = Field(None, pattern=ASCII_TEXT)
    mitigation_type : list[MitigationCategoryType] | None = None
    required: bool | None = None
    similar_to_coef: float | None = None
    reasoning: str | None = None
