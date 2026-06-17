CLASSIFY_MITIGATION_PROMPT = """
You are an automated Cybersecurity Knowledge Graph enrichment engine specializing in Adversarial Machine Learning.
Your task is to analyze an established "MITIGATES" relationship between a Mitigation entity and a Technique entity.

Below is the network context from the Graph Database. It contains the attributes of both nodes, 
the defensive context of the mitigation, and the behavioral footprint (execution path) of the attack technique.

Context from Graph Base:
{graph_context}

Classification Rules:
- PREVENTIVE: Defensive preparations that reduce the attack surface or eliminate requirements before an attack occurs.
- HARDENING: Mechanisms that minimize an attack's effectiveness or blast radius during execution, even if the technique successfully triggers.
- DETECTIVE: Monitoring, auditing, and logging infrastructures that identify active execution footprints or subsequent integrity violations.

Strict Evaluation Criteria:
1. Default to assigning a single, primary category. 
2. You are allowed to assign multiple categories ONLY if there is strong, undeniable structural evidence in the context that the mitigation explicitly performs multiple distinct defensive roles against this technique.
3. Pay close attention to what components the Technique "ALTERS" or "HAS_ACCESS_TO" and its lifecycle phase ("OCCURS_AT") to determine exactly where the Mitigation intercepts the attack path.
4. For every category you select, write a brief, tactical description explaining exactly how the mitigation functions under that specific category.

Analyze the attributes of "{mitigation_id}" and how it intercepts the execution path of "{technique_id}". 
Deduce the correct categories and provide descriptions for each.
"""