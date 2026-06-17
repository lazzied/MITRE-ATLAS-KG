

MITIGATION_CONTEXT_QUERY="""
MATCH (source_node:Mitigation {id: $mitigation_id})
OPTIONAL MATCH (source_node)-[r]->(target_nodes)
RETURN source_node, collect({
    rel_type: type(r), 
    target_labels: labels(target_nodes), 
    target_props: properties(target_nodes)
}) as topology

"""

TECHNIQUE_CONTEXT_QUERY = """
MATCH (source_node:Technique {id: $technique_id})
OPTIONAL MATCH (source_node)-[r]->(target_nodes)
RETURN source_node, collect({
    rel_type: type(r), 
    target_labels: labels(target_nodes), 
    target_props: properties(target_nodes)
}) as topology
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
