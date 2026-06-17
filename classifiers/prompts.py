MITIGATION_PROMPT = """
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


HAS_ACCESS_TO_PROMPT = """
Role: You are an expert Adversarial Machine Learning (AML) security engineer building a knowledge graph framework based on the MITRE ATLAS matrix. Your job is to extract access dependencies between an offensive Technique and fundamental Machine Learning Model Components.

    === TARGET MODEL COMPONENT OPTIONS ===
    - training_samples
    - training_labels
    - test_samples
    - test_labels
    - weights
    - output

    === RELATIONSHIP STRUCTURING CRITERIA ===
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

    === CURRENT TASK TO EVALUATE ===
    Using the extraction logic and grounding patterns demonstrated above, process the following live graph context:

    {graph_context}

    Analyze the attributes of "{technique_id}" and its neighborhood. Extract all valid access_requirements conforming to the strict validation rules.
    
"""

OCCURS_AT_PROMPT= """
Role: You are an expert Adversarial Machine Learning (AML) security engineer building a knowledge graph framework based on the MITRE ATLAS matrix. Your job is to extract lifecycle dependencies mapping an offensive Technique to its specific Attack Phase.

=== GRAPH DATA CONTEXT ===
{graph_context}

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

Determine all valid OCCURS_AT relationships for "{technique_id}".
"""
ALTERS_PROMPT= """
    Role: You are an expert Adversarial Machine Learning (AML) security engineer building a knowledge graph framework based on the MITRE ATLAS matrix. Your job is to extract alteration dependencies between an offensive Technique and fundamental Machine Learning Model Components.

    === TARGET MODEL COMPONENT OPTIONS ===
    - training_samples
    - training_labels
    - test_samples
    - test_labels
    - weights
    - output

    === RELATIONSHIP STRUCTURING CRITERIA ===
    Evaluate the relationship between the Technique ({technique_id}) and each target component based on these strict guidelines:
    - REQUIRED (required = true): The technique definitely requires, manipulates, or forces a modification of this component to execute its core vector.
    - SOMETIMES REQUIRED (required = false): The technique conditionally alters this component, or alters it only in specific sub-variants of the attack.
    - NOT REQUIRED (Omit from output list entirely): There is no interaction or modification path. Do not create an ALTERS relationship.

    === FEW-SHOT EXAMPLES FOR SYSTEM ALIGNMENT ===

    Example 1: Poisoning, bilevel
    - training_samples: REQUIRED (Directly manipulates data going into the training pipeline pool)
    - training_labels: SOMETIMES REQUIRED (Alters training labels conditionally depending on optimization target)
    - test_samples / test_labels / weights / output: NOT REQUIRED (No active modification or alteration happens to these components)

    Example 2: Backdoor (Trojaning Attack)
    - training_samples: REQUIRED (Must inject a trigger into the training data pool)
    - training_labels: SOMETIMES REQUIRED (May alter or corrupt labels to map to the backdoor target class)
    - test_samples: REQUIRED (Alters or appends the trigger matrix onto input evaluation/test instances at inference time)
    - test_labels / weights / output: NOT REQUIRED

    Example 3: Evasion, black-box
    - test_samples: REQUIRED (The adversary actively perturbs test or evaluation samples to dodge classification boundary limits)
    - output: SOMETIMES REQUIRED (Adversary might actively manipulate or intercept inference responses in some advanced pipeline variants)
    - training_samples / training_labels / weights / test_labels: NOT REQUIRED

    Example 4: Attribute Inference
    - All components: NOT REQUIRED (This attack is purely passive reconstruction/exfiltration; no pipeline elements are altered. Output is empty list)

    === STRICT ONE-TO-MANY VALIDATION RULES ===
    1. A single Technique CAN have a One-to-Many mapping to multiple Model Components (as demonstrated in the examples).
    2. Crucial Guardrail: You are allowed to map multiple components ONLY if there is direct, strong, and undeniable text-based evidence in the provided graph context showing the technique actively alters or modifies those distinct artifacts.
    3. If the evidence for an alteration path is speculative or purely hypothetical, you MUST drop that component from the list completely.

    === CURRENT TASK TO EVALUATE ===
    Using the extraction logic and grounding patterns demonstrated above, process the following live graph context:

    {graph_context}

    Analyze the attributes of "{technique_id}" and its neighborhood. Extract all valid alters_requirements.
    """
    
VIOLATES_PROMPT = """
    Role: You are an expert Adversarial Machine Learning (AML) triage analyst building a knowledge graph based on the MITRE ATLAS framework. Your task is to analyze an offensive Technique and map out its impact on core Security Objectives.

    === GRAPH DATA CONTEXT ===
    {graph_context}

    === LEGAL PREDEFINED STRINGS FOR THE 'descriptions' LIST ===
    You MUST extract descriptions verbatim from these sets. Do not reword, combine, or invent string tokens.

    CONFIDENTIALITY Options:
    {confidentiality_options}

    INTEGRITY Options:
    {integrity_options}

    AVAILABILITY Options:
    {availability_options}

    === MULTI-LABEL STRUCTURING RULES ===
    1. A single edge to a Security Objective CAN contain multiple description strings simultaneously (as a List), but ONLY if there is clear, undeniable text-grounded evidence in the context.
    2. Default to assigning the most accurate primary descriptions. Do not add supplementary descriptions if they are speculative or merely generic downstream outcomes.

    === SYSTEM FEW-SHOT ALIGNMENT REFERENCE===
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

    === LIVE EXTRACTION PROCESS ===
    Analyze the attributes of "{technique_id}" along with its connected tactics and case studies. Identify all applicable security objectives, populate their allowed descriptions lists, and output the structured tracking payloads.
    """
    
    
TECHNIQUE_SIMILARITY_PROMPT = """
You are an expert cybersecurity architect specializing in adversarial machine learning and the MITRE ATLAS framework.
Your task is to analyze two distinct attack techniques and provide a concise, text-grounded justification explaining why they are structurally and behaviorally similar.

You are given the exact mathematical similarity coefficient and the structural relationship footprints retrieved from our system graph database.

TARGET TECHNIQUE 1:
- ID: {technique_id_1}
- Structural Vectors: {profile_1}

COMPARED TECHNIQUE 2:
- ID: {technique_id_2}
- Structural Vectors: {profile_2}

EVALUATION METRICS:
- Final Calculated Similarity Coefficient: {final_score} (On a scale of 0.0 to 1.0, where 1.0 is identical)

CRITICAL INSTRUCTIONS:
1. Review the shared assets between both techniques: look for overlapping tactics, lifecycle phases (Training vs Inference), infrastructure access requirements, and targeted model components (e.g., datasets, hyperparameters, architecture).
2. Write a single, cohesive, high-quality explanation summarizing why these techniques are clustered together.
3. Focus purely on technical, behavioral, and structural commonalities. 
4. Do not include or repeat any JSON markup, markdown syntax headers, or wrapper text outside of your direct statement.

Your output must strictly fulfill the following Pydantic schema contract:
{{"justification": "Your clear, text-grounded cybersecurity reasoning here."}}
"""

CASE_STUDY_SIMILARITY_PROMPT = """ You are an elite cyber threat intelligence analyst tracking adversarial machine learning campaigns.
        Our graph similarity matrices have calculated a definitive behavioral overlap score of {final_score} between two case studies.

        CASE STUDY 1: {name_1} ({id_1})
        CASE STUDY 2: {name_2} ({id_2})

        STRUCTURAL MATRIX ANALYSIS:
        - Exact Overlapping Techniques: {exact_techniques}
        - Soft-Matched Closest Techniques: {soft_matches}

        Your task is to write a single, professional paragraph explaining why these two campaigns are clustered together.
        Focus on the shared adversarial vectors, targeted pipeline components, or operational intentions demonstrated. 
        Do not mention, question, or change the mathematical score provided. Output your evaluation purely inside the schema contract.
"""
