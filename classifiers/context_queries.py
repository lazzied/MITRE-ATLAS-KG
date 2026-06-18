

MITIGATION_CONTEXT_QUERY="""
MATCH (source_node:Mitigation {id: $entity_id})
OPTIONAL MATCH (source_node)-[r]->(target_nodes)
RETURN source_node, collect({
    rel_type: type(r), 
    target_labels: labels(target_nodes), 
    target_props: properties(target_nodes)
}) as topology

"""

TECHNIQUE_CONTEXT_QUERY = """
MATCH (source_node:Technique {id: $entity_id})
OPTIONAL MATCH (source_node)-[r]->(target_nodes)
RETURN source_node, collect({
    rel_type: type(r), 
    target_labels: labels(target_nodes), 
    target_props: properties(target_nodes)
}) as topology
"""

CASE_STUDY_QUERY = """
MATCH (source_node:CaseStudy {id: $entity_id})
OPTIONAL MATCH (source_node)-[:DEMONSTRATES]->(t:Technique)
RETURN source_node, collect({
    rel_type: "DEMONSTRATES",
    target_labels: labels(t),
    target_props: properties(t)
}) as topology
"""
