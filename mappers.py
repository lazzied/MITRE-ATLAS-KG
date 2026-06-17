from atlas.enums import MitigationLifecyclePhasesType, TechniquePlatformType
from scripts.schemas import AttackPhaseType, ModelComponentType, SecurityObjectiveType

 # these are mappers for descriptions and ID

MITIGATION_LIFECYCLE_PHASE_DESCRIPTIONS = {
    MitigationLifecyclePhasesType.DATA_UNDERSTANDING: (
        "Activities related to understanding business objectives, defining AI system requirements, "
        "identifying stakeholders, collecting data sources, and assessing data quality, risks, and constraints."
    ),

    MitigationLifecyclePhasesType.DATA_PREPARATION: (
        "Activities involving data collection, cleaning, transformation, labeling, augmentation, "
        "feature engineering, validation, and preparation for model development."
    ),

    MitigationLifecyclePhasesType.MODEL_ENGINEERING: (
        "Activities focused on designing, training, tuning, and optimizing AI models, including "
        "model architecture selection and experimentation."
    ),

    MitigationLifecyclePhasesType.MODEL_EVALUATION: (
        "Activities for assessing model performance, robustness, fairness, security, explainability, "
        "and compliance against defined requirements and metrics."
    ),

    MitigationLifecyclePhasesType.DEPLOYMENT: (
        "Activities required to release AI models into production environments, including integration, "
        "serving infrastructure, access controls, and operational readiness."
    ),

    MitigationLifecyclePhasesType.MONITORING: (
        "Activities for continuously monitoring model behavior, detecting drift, managing incidents, "
        "maintaining performance, updating models, and ensuring long-term governance."
    ),
}


PLATFORM_DESCRIPTIONS = {
    TechniquePlatformType.PREDICTIVE: (
        "AI systems designed to analyze historical or current data to predict outcomes, "
        "classify information, detect patterns, or support decision-making. Examples include "
        "fraud detection, recommendation systems, and predictive maintenance models."
    ),

    TechniquePlatformType.GENERATIVE: (
        "AI systems capable of generating new content such as text, images, audio, video, "
        "code, or structured data. Examples include large language models, image generation "
        "models, and code assistants."
    ),

    TechniquePlatformType.AGENTIC: (
        "AI systems that can autonomously plan, reason, make decisions, and execute actions "
        "toward goals, often by interacting with tools, environments, APIs, or other agents."
    ),

    TechniquePlatformType.ENTERPRISE: (
        "Organizational and operational AI infrastructure, processes, governance, and platforms "
        "that support the development, deployment, management, security, and monitoring of AI "
        "systems across the enterprise."
    ),
}

EXPLOIT_RELATIONSHIP_DESCRIPTION = {
   SecurityObjectiveType.CONFIDENTIALITY: (
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
    ),

    SecurityObjectiveType.INTEGRITY: (
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
    ),

    SecurityObjectiveType.AVAILABILITY: (
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
    ),
}

SECURITY_OBJECTIVE_DESCRIPTION = {
    SecurityObjectiveType.CONFIDENTIALITY:
        "Ensures model and data information cannot be obtained by unauthorized parties.",

    SecurityObjectiveType.INTEGRITY:
        "Ensures model behavior and outputs cannot be maliciously manipulated.",

    SecurityObjectiveType.AVAILABILITY:
        "Ensures AI systems remain operational and effective for legitimate users.",
}

ATTACK_PHASE_DESCRIPTION = {
    AttackPhaseType.INFERENCE: (
        "Activities performed after an AI model has been trained and is being queried, "
        "served, evaluated, or otherwise used to produce outputs. In this phase, attacks "
        "often target model behavior, inputs, prompts, runtime access paths, responses, "
        "or exposed inference APIs."
    ),

    AttackPhaseType.TRAINING: (
        "Activities performed while data, labels, features, architectures, parameters, "
        "or learning procedures are being used to build or update an AI model. In this "
        "phase, attacks often target the training pipeline, datasets, labeling process, "
        "optimization procedure, or model state before deployment."
    ),
}

MODEL_COMPONENT_DESCRIPTION = {
    ModelComponentType.TRAINING_SAMPLES: (
        "Input examples used during model training to teach patterns, features, behaviors, "
        "or decision boundaries. Compromise of these samples can introduce poisoned data, "
        "private information exposure, biased behavior, or persistent weaknesses in the "
        "trained model."
    ),

    ModelComponentType.TRAINING_LABELS: (
        "Ground-truth annotations, classes, ratings, or target values associated with "
        "training samples. Compromise of these labels can corrupt supervised learning, "
        "create targeted misclassification behavior, weaken detection quality, or shift "
        "model decisions toward attacker-chosen outcomes."
    ),

    ModelComponentType.TEST_SAMPLES: (
        "Input examples reserved for evaluating model performance, robustness, fairness, "
        "or security after training. Compromise of these samples can hide weaknesses, "
        "distort evaluation results, or make a model appear safer or more accurate than "
        "it is under real operating conditions."
    ),

    ModelComponentType.TEST_LABELS: (
        "Expected answers, classes, or target values used to score model behavior on test "
        "samples. Compromise of these labels can manipulate evaluation metrics, conceal "
        "model failures, or cause incorrect acceptance of unsafe model versions."
    ),

    ModelComponentType.WEIGHTS: (
        "Learned model parameters that encode behavior after training or fine-tuning. "
        "Compromise of weights can reveal proprietary model information, enable model "
        "theft, introduce hidden behavior, degrade performance, or alter deployed model "
        "outputs."
    ),

    ModelComponentType.OUTPUT: (
        "Predictions, classifications, generated content, scores, decisions, or actions "
        "produced by an AI system during evaluation or operation. Compromise of outputs "
        "can mislead users, trigger unsafe downstream actions, leak sensitive information, "
        "or violate confidentiality, integrity, or availability objectives."
    ),
}




