
#Queries Neo4j for the local neighborhood of the edge, builds the context,
CLASSIFY_MITIGATION_CONTEXT_QUERY = """
MATCH (m:Mitigation {id: $mitigation_id})-[r:MITIGATES]->(t:Technique {id: $technique_id})

// Step uno: Collect immediate mitigation surroundings safely
OPTIONAL MATCH (m)-[r_mit]-(m_neighbor)
WITH m, t, collect({rel: type(r_mit), neighbor: properties(m_neighbor)}) AS mit_context

// Step dos: Collect technique behavior, explicitly ignoring the source mitigation node
OPTIONAL MATCH (t)-[r_tech]-(t_neighbor)
WHERE t_neighbor <> m
RETURN m, t, mit_context, collect({rel: type(r_tech), neighbor: properties(t_neighbor)}) AS tech_context
"""
