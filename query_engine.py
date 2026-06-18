from enum import Enum
from typing import List
from llama_index.core import StorageContext
from llama_index.core.query_engine import KnowledgeGraphQueryEngine
from llama_index.core.response_synthesizers import Refine
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from scripts.classifiers.initialization import get_connections
from scripts.prompt_guide import  DOCUMENT_DRAFTING_TEMPLATE, INTENT_ROUTER_TEMPLATE, REASONING_ENGINE_TEMPLATE, STANDARD_QUERY_TEMPLATE
from scripts.schemas import EntityType, RelationshipType

INTENT_ROUTER_PROMPT = """
role:
You are an AI Security Knowledge Graph Query Router.

task:
Classify the user request into EXACTLY ONE route.

Available Routes:

reasoning_engine
- AI architecture analysis
- threat modeling
- attack surface assessment
- exposure analysis
- security evaluation of a system design

document_drafting
- reports
- executive summaries
- threat intelligence documents
- threat model documents
- comprehensive security assessments

standard
- graph questions
- fact retrieval
- relationship exploration
- mitigation lookups
- technique lookups
- general knowledge graph queries

Select the single best route.

User Request:
{query_str}
"""
RETRIEVAL_PLANNER_PROMPT = """
You are an AML Knowledge Graph Retrieval Planner.

Ontology:

Nodes classes:
- CaseStudy
- Technique
- Tactic
- Mitigation
- Platform
- LifeCyclePhase
- ModelComponent
- SecurityObjective
- AttackPhase

Relationships:
- employs
- achieves
- alters
- has_access_to
- occurs_at
- violates
- applies_to_platform
- mitigates
- applies_in_phase
- specializes

Task:

Identify the minimum set of entities and relationships
required to answer the question.

this is the context/direction of the question:
{route_prompt}

Question:
{query_str}
"""
REASONING_ENGINE_PROMPT=""
DOCUMENT_DRAFTING_PROMPT=""
STANDARD_PROMPT=""


class Route(str, Enum):
    REASONING_ENGINE = "reasoning_engine"
    DOCUMENT_DRAFTING = "document_drafting"
    STANDARD = "standard"


class RouteResponseSchema(BaseModel):
    route: Route = Field(
        description="The selected routing destination."
    )
    reasoning: str = Field(
        description = ""
    )
    
    
ROUTE_PROMPT_MAPPER = {
    Route.REASONING_ENGINE: REASONING_ENGINE_PROMPT,
    Route.DOCUMENT_DRAFTING: DOCUMENT_DRAFTING_PROMPT,
    Route.STANDARD: STANDARD_PROMPT,
}
    
    
class RetrievalPlanSchema(BaseModel):
    entities: List[EntityType] = Field(
        description="Relevant node labels."
    )

    relationships: List[RelationshipType] = Field(
        description="Relevant relationship types."
    )

    reasoning: str = Field(
        description="Why these graph elements are needed."
    )


def route_query(user_prompt: str) -> Route:
    graph_store, llm = get_connections()

    program = LLMTextCompletionProgram.from_defaults(
        output_cls=RouteResponseSchema,
        prompt_template_str=INTENT_ROUTER_PROMPT,
        llm=llm,
        verbose=False,
    )

    response: RouteResponseSchema = program(
        query_str=user_prompt
    )

    return response.route

def build_retrieval_plan(user_query: str, route: Route) -> RetrievalPlanSchema: # this will get the concerned nodes and relationships
    _, llm = get_connections()

    program = LLMTextCompletionProgram.from_defaults(
        output_cls=RetrievalPlanSchema,
        prompt_template_str=RETRIEVAL_PLANNER_PROMPT,
        llm=llm,
        verbose=False,
    )

    plan: RetrievalPlanSchema = program(
        query_str=user_query
    )

    return plan

# step 1: get concerned entities + relationships types
# step 2: get the concerned entities with their ids and 

template_map = {
    
    "REASONING_ENGINE": REASONING_ENGINE_TEMPLATE,
    "DOCUMENT_DRAFTING": DOCUMENT_DRAFTING_TEMPLATE,
    "STANDARD_QUERY": STANDARD_QUERY_TEMPLATE,
    
}

selected_template = template_map[intent]


