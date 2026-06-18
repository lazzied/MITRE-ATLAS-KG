MITIGATION_PROMPT = """
Role: You are an automated Cybersecurity Knowledge Graph enrichment engine specializing in Adversarial Machine Learning.
Task: Your task is to analyze an established "MITIGATES" relationship between a Mitigation entity and a Technique entity.

TARGET RELATIONSHIP EVALUATION: MITIGATION -[MITIGATES]-> TECHNIQUE

=== TARGET CATEGORY OPTIONS ===
- PREVENTIVE: Defensive preparations that reduce the attack surface or eliminate requirements before an attack occurs.
- HARDENING: Mechanisms that minimize an attack's effectiveness or blast radius during execution, even if the technique successfully triggers.
- DETECTIVE: Monitoring, auditing, and logging infrastructures that identify active execution footprints or subsequent integrity violations.

=== FEW-SHOT EXAMPLES FOR SYSTEM ALIGNMENT ===

Example 1: Sanitize Training Data -[MITIGATES]-> Poisoning, label flip
- PREVENTIVE: (Filtering and validating training_samples/training_labels before ingestion removes the poisoned data the technique depends on, eliminating the requirement before training begins)

Example 2: Adversarial Input Detection -[MITIGATES]-> Evasion, white-box
- DETECTIVE: (Statistical or model-based detectors flag perturbed test_samples at inference time, identifying the active execution footprint of the technique)

Example 3: Rate Limiting / Query Throttling -[MITIGATES]-> Model Stealing
- HARDENING: (Capping the volume of queries against the output endpoint limits how much functional information an adversary can extract per unit time, reducing blast radius without preventing querying altogether)
- DETECTIVE: (Anomalous query volume patterns can also be logged and flagged, identifying the active extraction attempt as it occurs)

Example 4: Encrypted Model Storage -[MITIGATES]-> Model Stealing
- PREVENTIVE: (Encrypting weights at rest removes the adversary's ability to directly access model parameters, eliminating a precondition for white-box extraction)

=== STRICT EVALUATION CRITERIA ===
1. Default to assigning a single, primary category.
2. You are allowed to assign multiple categories ONLY if there is strong, undeniable structural evidence in the context that the mitigation explicitly performs multiple distinct defensive roles against this technique.
3. Pay close attention to what components the Technique "ALTERS" or "HAS_ACCESS_TO" and its lifecycle phase ("OCCURS_AT") to determine exactly where the Mitigation intercepts the attack path.
4. For every category you select, write a brief, tactical description explaining exactly how the mitigation functions under that specific category.

=== GRAPH DATA CONTEXT ===
Below is the network context from the Graph Database. It contains the attributes of both nodes,
the defensive context of the mitigation, and the behavioral footprint (execution path) of the attack
technique, including its ALTERS, HAS_ACCESS_TO, and OCCURS_AT edges.

{graph_context}

=== LIVE EXTRACTION PROCESS ===
Analyze the attributes of "{mitigation_id}" and how it intercepts the execution path of "{technique_id}".
Deduce the correct categories and provide descriptions for each.
"""


HAS_ACCESS_TO_PROMPT = """
Role: You are an expert Adversarial Machine Learning (AML) security engineer building a knowledge graph framework based on the MITRE ATLAS matrix.
Task: Your job is to extract access dependencies between an offensive Technique and fundamental Machine Learning Model Components.

TARGET RELATIONSHIP EVALUATION: TECHNIQUE -[HAS_ACCESS_TO]-> MODEL COMPONENT

=== TARGET MODEL COMPONENT OPTIONS ===
- training_samples
- training_labels
- test_samples
- test_labels
- weights
- output

=== RELATIONSHIP STRUCTURING CRITERIA ===
THE "REQUIRED" ATTRIBUTE OF THE RELATIONSHIP FOLLOWS THIS CRITERIA:
- REQUIRED (required = true): The attack technique physically CANNOT execute or achieve its primary goal without this component.
- OPTIONAL (required = false): The technique can function without it, but access to it optimizes the attack, represents an alternative variant, or is conditionally required.
- NO RELATIONSHIP: Do not include the component in the output list if the technique does not interact with it.

=== FEW-SHOT EXAMPLES FOR SYSTEM ALIGNMENT ===

Example 1: Poisoning, bilevel (Data Poisoning Attack) -> [Valid One-to-Many Output]
- training_samples: REQUIRED (The adversary must inject or manipulate data entering the training pool)
- training_labels: REQUIRED (The attack relies on modifying or knowing corresponding training labels for optimization)
- weights: OPTIONAL (A cleaner optimization can be achieved if weights are known, but white-box access isn't strictly mandatory)
- test_samples / test_labels / output: NO RELATIONSHIP (The attack is executed entirely during the pre-deployment phase)

Example 2: Evasion, white-box (Adversarial Perturbation) -> [Valid One-to-Many Output]
- test_samples: REQUIRED (The adversary manipulates current input evaluation samples)
- test_labels: REQUIRED (Needed to calculate loss vector adjustments away from the true target label)
- weights: REQUIRED (White-box explicitly mandates direct access to model layers, parameters, and gradients)
- training_samples / training_labels: NO RELATIONSHIP

Example 3: Model Stealing (Functional Replication) -> [Valid One-to-Many Output]
- output: REQUIRED (The adversary must query the model's inference API and observe returned labels or confidence scores)
- test_samples: OPTIONAL (The attacker can use a separate synthetic dataset to query the target black-box API)
- training_samples / training_labels / weights: NO RELATIONSHIP

=== STRICT ONE-TO-MANY VALIDATION RULES ===
1. A single Technique CAN have a One-to-Many mapping to multiple Model Components (as demonstrated in the examples).
2. Crucial Guardrail: You are allowed to map multiple components ONLY if there is direct, strong, and undeniable text-based evidence in the provided graph context showing the technique actively touches or targets those distinct artifacts.
3. If the evidence for a component is speculative, conditional on an edge-case configuration not mentioned in the context, or purely hypothetical, you MUST drop that component from the list completely. Prioritize high-confidence grounding over exhaustive mapping.

=== GRAPH DATA CONTEXT ===
Below is the network context from the Graph Database. It contains the attributes of both nodes.

{graph_context}

=== LIVE EXTRACTION PROCESS ===
Analyze the attributes of "{technique_id}" and its neighborhood. Extract all valid access_requirements conforming to the strict validation rules.
"""


OCCURS_AT_PROMPT = """
Role: You are an expert Adversarial Machine Learning (AML) security engineer building a knowledge graph framework based on the MITRE ATLAS matrix.
Task: Your job is to extract lifecycle dependencies mapping an offensive Technique to its specific Attack Phase.

TARGET RELATIONSHIP EVALUATION: TECHNIQUE -[OCCURS_AT]-> ATTACK_PHASE

=== TARGET ATTACK PHASE OPTIONS ===
- training: Pre-deployment pipeline operations. Includes dataset curation, labeling configurations, training execution, optimization cycles, and model supply-chain storage.
- inference: Post-deployment production operations. Includes querying the live API, sending production payloads, processing model outputs, monitoring telemetry, or attacking deployed edge models.

=== LIFECYCLE CLASSIFICATION PROTOCOL ===
Analyze the technical description of the technique and any associated operational Case Studies:
1. Map to "training" if the adversary acts while the model is actively learning or being built.
2. Map to "inference" if the adversary acts against a frozen, deployed model responding to operational queries.
3. You may assign BOTH phases if and only if the technique exhibits clear multi-variant execution traits across the dataset (e.g., a technique that poisons training data but requires a secondary payload insertion at test time). Otherwise, stick to the primary phase.

=== LIFECYCLE REFERENCE EXAMPLES ===
- Poisoning, bilevel -> phase_id: training (Manipulates the training optimization space)
- Poisoning, label flip -> phase_id: training (Corrupts training annotations before model fitting)
- Backdoor -> phase_id: training AND phase_id: inference (Requires injecting a trigger into training, and triggering the payload during inference test queries)
- Evasion (White-box/Black-box) -> phase_id: inference (Perturbs inputs against an active, deployed inference pipeline)
- Model Stealing -> phase_id: inference (Queries the deployment API to extract outputs and map internal parameters)

=== GRAPH DATA CONTEXT ===
Below is the network context from the Graph Database. It contains the attributes of both nodes.

{graph_context}

=== LIVE EXTRACTION PROCESS ===
Determine all valid OCCURS_AT relationships for "{technique_id}".
"""


ALTERS_PROMPT = """
Role: You are an expert Adversarial Machine Learning (AML) security engineer building a knowledge graph framework based on the MITRE ATLAS matrix.
Task: Your job is to extract alteration dependencies between an offensive Technique and fundamental Machine Learning Model Components.

TARGET RELATIONSHIP EVALUATION: TECHNIQUE -[ALTERS]-> MODEL COMPONENT

=== TARGET MODEL COMPONENT OPTIONS ===
- training_samples
- training_labels
- test_samples
- test_labels
- weights
- output

=== RELATIONSHIP STRUCTURING CRITERIA ===
THE "REQUIRED" ATTRIBUTE OF THE RELATIONSHIP FOLLOWS THIS CRITERIA (same scheme as HAS_ACCESS_TO, applied to active modification rather than mere access):
- REQUIRED (required = true): The technique physically CANNOT achieve its primary goal without actively altering this component.
- OPTIONAL (required = false): The technique alters this component only in some variants or configurations; alteration is conditional, not universal across the technique's execution.
- NO RELATIONSHIP: Do not include the component in the output list if the technique does not alter it.

=== FEW-SHOT EXAMPLES FOR SYSTEM ALIGNMENT ===

Example 1: Poisoning, bilevel
- training_samples: REQUIRED (Directly manipulates data going into the training pipeline pool)
- training_labels: OPTIONAL (Alters training labels conditionally, depending on the optimization target)
- test_samples / test_labels / weights / output: NO RELATIONSHIP (No active modification happens to these components)

Example 2: Backdoor (Trojaning Attack)
- training_samples: REQUIRED (Must inject a trigger pattern into the training data pool)
- training_labels: OPTIONAL (May alter or corrupt labels to map to the backdoor target class, depending on the variant)
- test_samples: REQUIRED (Alters or appends the trigger pattern onto input evaluation/test instances at inference time)
- test_labels / weights / output: NO RELATIONSHIP

Example 3: Evasion, black-box
- test_samples: REQUIRED (The adversary actively perturbs test or evaluation samples to dodge classification boundary limits)
- output: OPTIONAL (Adversary might actively manipulate or intercept inference responses in some advanced pipeline variants)
- training_samples / training_labels / weights / test_labels: NO RELATIONSHIP

Example 4: Attribute Inference
- All components: NO RELATIONSHIP (This attack is purely passive reconstruction/exfiltration; no pipeline elements are altered. Output is an empty list)

=== STRICT ONE-TO-MANY VALIDATION RULES ===
1. A single Technique CAN have a One-to-Many mapping to multiple Model Components (as demonstrated in the examples).
2. Crucial Guardrail: You are allowed to map multiple components ONLY if there is direct, strong, and undeniable text-based evidence in the provided graph context showing the technique actively alters or modifies those distinct artifacts.
3. If the evidence for an alteration path is speculative or purely hypothetical, you MUST drop that component from the list completely.

=== GRAPH DATA CONTEXT ===
Below is the network context from the Graph Database. It contains the attributes of both nodes.

{graph_context}

=== LIVE EXTRACTION PROCESS ===
Analyze the attributes of "{technique_id}" and its neighborhood. Extract all valid alters_requirements conforming to the strict validation rules.
"""


VIOLATES_PROMPT = """
Role: You are an expert Adversarial Machine Learning (AML) triage analyst building a knowledge graph based on the MITRE ATLAS framework.
Task: Your task is to analyze an offensive Technique and map out its impact on core Security Objectives.

TARGET RELATIONSHIP EVALUATION: TECHNIQUE -[VIOLATES]-> SECURITY_OBJECTIVE

=== LEGAL PREDEFINED STRINGS FOR THE 'descriptions' LIST ===
You MUST extract descriptions verbatim from these sets. Do not reword, combine, or invent string tokens.

CONFIDENTIALITY Options:
    "Copy model without consent",
    "Steal model functionality",
    "Extract model parameters",
    "Extract model architecture",
    "Infer sample membership",
    "Infer training data attributes",
    "Reconstruct training samples",
    "Recover sensitive training data",
    "Obtain proprietary model information",
    "Leak confidential information",

INTEGRITY Options:
    "Misclassify perturbed samples",
    "Misclassify samples with trigger",
    "Cause targeted misclassification",
    "Cause untargeted misclassification",
    "Manipulate model outputs",
    "Manipulate model behavior",
    "Poison training data",
    "Poison training labels",
    "Backdoor the model",
    "Influence model decisions",
    "Bypass safety controls",
    "Evade detection",
    "Subvert intended model behavior",

AVAILABILITY Options:
    "Decrease model performance",
    "Decrease model accuracy",
    "Increase inference latency",
    "Increase computational cost",
    "Increase resource consumption",
    "Prevent model training",
    "Prevent model inference",
    "Cause denial of service",
    "Disrupt model operation",
    "Reduce model utility",
    "Cause system outage",

=== MULTI-LABEL STRUCTURING RULES ===
1. A single edge to a Security Objective CAN contain multiple description strings simultaneously (as a List), but ONLY if there is clear, undeniable text-grounded evidence in the context.
2. Default to assigning the most accurate primary descriptions. Do not add supplementary descriptions if they are speculative or merely generic downstream outcomes.
3. Cross-reference the technique's ALTERS, HAS_ACCESS_TO, and OCCURS_AT edges where available in the context: what a technique alters or accesses is strong supporting evidence for which Security Objective it violates (e.g., altering weights or output points toward integrity/availability concerns, while accessing output without altering anything points toward confidentiality).

=== SYSTEM FEW-SHOT ALIGNMENT REFERENCE ===
Use these standard baselines to guide your classification thresholds:

- Poisoning, bilevel
  * Objective: availability -> ["Decrease model performance"]
  * Confidentiality: NO RELATIONSHIP | Integrity: NO RELATIONSHIP

- Poisoning, label flip
  * Objective: availability -> ["Decrease model performance"]
  * Confidentiality: NO RELATIONSHIP | Integrity: NO RELATIONSHIP

- Backdoor
  * Objective: integrity -> ["Misclassify samples with trigger"]
  * Confidentiality: NO RELATIONSHIP | Availability: NO RELATIONSHIP

- Evasion, white-box
  * Objective: integrity -> ["Misclassify perturbed samples"]
  * Confidentiality: NO RELATIONSHIP | Availability: NO RELATIONSHIP

- Evasion, black-box
  * Objective: integrity -> ["Misclassify perturbed samples"]
  * Confidentiality: NO RELATIONSHIP | Availability: NO RELATIONSHIP

- Model Stealing
  * Objective: confidentiality -> ["Copy model without consent"]
  * Integrity: NO RELATIONSHIP | Availability: NO RELATIONSHIP

- Membership Inference (Mem. Inf.)
  * Objective: confidentiality -> ["Infer sample membership"]
  * Integrity: NO RELATIONSHIP | Availability: NO RELATIONSHIP

- Attribute Inference (Attribute Inf.)
  * Objective: confidentiality -> ["Infer training data attributes"]
  * Integrity: NO RELATIONSHIP | Availability: NO RELATIONSHIP

=== GRAPH DATA CONTEXT ===
Below is the network context from the Graph Database. It contains the technique's attributes, connected
tactics, case studies, and any available ALTERS / HAS_ACCESS_TO / OCCURS_AT edges.

{graph_context}

=== LIVE EXTRACTION PROCESS ===
Analyze the attributes of "{technique_id}" along with its connected tactics, case studies, and neighborhood
edges. Identify all applicable security objectives, populate their allowed descriptions lists, and output
the structured tracking payloads.
"""
    
TECHNIQUE_SIMILARITY_PROMPT = """
You are an expert cybersecurity architect specializing in adversarial machine learning and the MITRE ATLAS framework.
Your task is to analyze two distinct attack techniques and provide a concise, text-grounded justification explaining why they are structurally and behaviorally similar.

You are given the combined local graph topologies and attributes of both entities below:

GRAPH CONTEXT METADATA:
{graph_context}

EVALUATION METRICS:
- Source Technique ID: {technique_id_1}
- Target Technique ID: {technique_id_2}
- Final Calculated Similarity Coefficient: {final_score} (Scale 0.0 to 1.0)

CRITICAL INSTRUCTIONS:
1. Review the shared assets between both techniques: look for overlapping tactics, lifecycle phases (Training vs Inference), infrastructure access requirements, and targeted model components.
2. Focus purely on technical, behavioral, and structural commonalities to justify the link.
3. Your output must strictly fulfill the following structural Pydantic schema layout, matching an inline array structure. Do not generate markdown code blocks or wrapper text outside the JSON payload.

Target Output JSON Schema Contract:
{{
    "entity_relationships": [
        {{
            "source_entity": "{technique_id_1}",
            "target_entity": "{technique_id_2}",
            "similarity_coeff": {final_score},
            "description": "Your clear, text-grounded architectural justification here.",
            "reasoning": "Brief technical sentence linking back to evidence parameters found in the graph context."
        }}
    ],
    "reasoning": "Overall high-level evaluation logic tying both models together."
}}
"""


CASE_STUDY_SIMILARITY_PROMPT = """
You are an elite cyber threat intelligence analyst tracking adversarial machine learning campaigns within the MITRE ATLAS framework.
Your task is to analyze two historical attack profiles and justify why their operational footprints align.

You are given the structural matrix analytics, alongside the local graph configurations of both profiles below:

GRAPH CONTEXT METADATA:
{graph_context}

EVALUATION METRICS:
- Source Case Study: {name_1} ({id_1})
- Target Case Study: {name_2} ({id_2})
- Exact Overlapping Techniques: {exact_techniques}
- Soft-Matched Closest Techniques: {soft_matches}
- Blended Mathematical Overlap Score: {final_score} (Scale 0.0 to 1.0)

CRITICAL INSTRUCTIONS:
1. Focus on the shared adversarial vectors, targeted pipeline vulnerabilities, or operational intentions demonstrated across both campaigns.
2. Do not mention, question, or parse the mathematical score directly within your final response descriptions.
3. Your output must strictly fulfill the following structural Pydantic schema layout, matching an inline array structure.

Target Output JSON Schema Contract:
{{
    "entity_relationships": [
        {{
            "source_entity": "{id_1}",
            "target_entity": "{id_2}",
            "similarity_coeff": {final_score},
            "description": "Your professional threat intelligence narrative paragraph here explaining campaign crossovers.",
            "reasoning": "Brief technical sentence linking back to evidence elements found in the graph context topology."
        }}
    ],
    "reasoning": "High-level threat intelligence logical tracking explaining why these two specific attack histories cluster together."
}}
"""