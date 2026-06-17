
#Queries Neo4j for the local neighborhood of the edge, builds the context,
MITIGATION_CONTEXT_QUERY = """
MATCH (m:Mitigation {id: $mitigation_id})-[r:MITIGATES]->(t:Technique {id: $technique_id})

// Step uno: Collect immediate mitigation surroundings safely
OPTIONAL MATCH (m)-[r_mit]-(m_neighbor)
WITH m, t, collect({rel: type(r_mit), neighbor: properties(m_neighbor)}) AS mit_context

// Step dos: Collect technique behavior, explicitly ignoring the source mitigation node
OPTIONAL MATCH (t)-[r_tech]-(t_neighbor)
WHERE t_neighbor <> m
RETURN m, t, mit_context, collect({rel: type(r_tech), neighbor: properties(t_neighbor)}) AS tech_context
"""

HAS_ACCESS_TO_CONTEXT_QUERY = """
MATCH (t:Technique {id: $technique_id})
// Pull local adversarial footprint context structures out cleanly
OPTIONAL MATCH (t)-[r]->(neighbors)
RETURN t, collect({
    rel_type: type(r), 
    neighbor_labels: labels(neighbors), 
    neighbor_props: properties(neighbors)
}) as neighborhood_map
"""

OCCURS_AT_CONTEXT_QUERY = """
MATCH (t:Technique {id: $technique_id})
// Bidirectional match configuration ensures complete operational background pulling
OPTIONAL MATCH (t)-[r]-(neighbors)
RETURN t, collect({
    rel_type: type(r), 
    neighbor_labels: labels(neighbors), 
    neighbor_props: properties(neighbors)
}) as neighborhood_map
"""
ALTERS_QUERY="""
    MATCH (t {id: $technique_id})
    OPTIONAL MATCH (t)-[r]->(neighbors)
    RETURN t, collect({
        rel_type: type(r), 
        neighbor_labels: labels(neighbors), 
        neighbor_props: properties(neighbors)
    }) as neighborhood_map
    """
    
VIOLATES_QUERY = """
    MATCH (t {id: $technique_id})
    OPTIONAL MATCH (t)-[r]->(neighbors)
    RETURN t, collect({
        rel_type: type(r), 
        neighbor_labels: labels(neighbors), 
        neighbor_props: properties(neighbors)
    }) as neighborhood_map
    """
TECHNIQUE_SIMILARITY_QUERY = """
        MATCH (current_tech {id: $tech_id})
        
        # Collect connected node IDs across each specific relationship type
        OPTIONAL MATCH (current_tech)-[:achieves]->(tactic)
        OPTIONAL MATCH (current_tech)-[:occurs_at]->(phase)
        OPTIONAL MATCH (current_tech)-[:has_access_to]->(access_component)
        OPTIONAL MATCH (current_tech)-[:alters]->(alter_component)
        OPTIONAL MATCH (current_tech)-[:specializes]->(parent_tech)
        
        RETURN 
            current_tech.id AS tech_id,
            collect(distinct tactic.id) AS associated_tactics,
            collect(distinct phase.id) AS associated_phases,
            collect(distinct access_component.id) AS access_requirements,
            collect(distinct alter_component.id) AS alter_requirements,
            parent_tech.id AS parent_id
        """


CASE_STUDY_SIMILARITY_QUERY = """  MATCH (c:CaseStudy {id: $case_id})
        OPTIONAL MATCH (c)-[:UTILIZED|:ADOPTED]->(t:Technique)
        RETURN c.id AS case_id, c.name AS name, collect(t.id) AS technique_ids
"""
