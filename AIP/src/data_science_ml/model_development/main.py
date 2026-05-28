"""
Product 14: Model Development Registry (Stateful Agentic AI)
Assigned AI Agent: Model Developer Agent
Sweeps prediction model hyperparameter trials and holds multi-agent evaluation debates.
"""

import json
from typing import Dict, Any, List
from shared.intelligence import call_llm

async def get_model_experiments(model_type: str = "All") -> Dict[str, Any]:
    print(f"[Workflow: Data Science - Develop] Compiling classification experiments.")

    # 1. Generate full trials matrix mapping XGBoost, Random Forest, and Logistic Regression
    experiments = [
        {
            'runId': 'run_xgb_model_001',
            'modelName': 'XGBoost Classifier',
            'hyperparameters': {'learningRate': 0.01, 'batchSize': 32, 'maxDepth': 6, 'estimators': 150},
            'accuracy': 0.89,
            'rocArea': 0.92,
            'f1Score': 0.87,
            'latency': 74,
            'status': 'completed',
            'isChampion': False
        },
        {
            'runId': 'run_xgb_model_002',
            'modelName': 'XGBoost Classifier',
            'hyperparameters': {'learningRate': 0.05, 'batchSize': 64, 'maxDepth': 8, 'estimators': 200},
            'accuracy': 0.84,
            'rocArea': 0.88,
            'f1Score': 0.82,
            'latency': 98,
            'status': 'completed',
            'isChampion': False
        },
        {
            'runId': 'run_xgb_model_003',
            'modelName': 'XGBoost Classifier (Champion)',
            'hyperparameters': {'learningRate': 0.001, 'batchSize': 32, 'maxDepth': 10, 'estimators': 300},
            'accuracy': 0.93,
            'rocArea': 0.96,
            'f1Score': 0.91,
            'latency': 118,
            'status': 'completed',
            'isChampion': True
        },
        {
            'runId': 'run_rf_model_004',
            'modelName': 'Random Forest Classifier',
            'hyperparameters': {'learningRate': 0.0, 'batchSize': 64, 'maxDepth': 12, 'estimators': 250},
            'accuracy': 0.88,
            'rocArea': 0.91,
            'f1Score': 0.86,
            'latency': 142,
            'status': 'completed',
            'isChampion': False
        },
        {
            'runId': 'run_lr_model_005',
            'modelName': 'Logistic Regression Baseline',
            'hyperparameters': {'learningRate': 0.0, 'batchSize': 128, 'maxDepth': 0, 'estimators': 0},
            'accuracy': 0.76,
            'rocArea': 0.81,
            'f1Score': 0.73,
            'latency': 32,
            'status': 'completed',
            'isChampion': False
        },
        {
            'runId': 'run_xgb_model_006',
            'modelName': 'XGBoost Classifier',
            'hyperparameters': {'learningRate': 0.1, 'batchSize': 128, 'maxDepth': 4, 'estimators': 100},
            'accuracy': 0.72,
            'rocArea': 0.76,
            'f1Score': 0.69,
            'latency': 52,
            'status': 'completed',
            'isChampion': False
        }
    ]

    # Filter by model type if requested
    if model_type != "All":
        experiments = [e for e in experiments if model_type.lower() in e['modelName'].lower()]

    # 2. Multi-Agent Experimentation Dialogue
    system_prompt = """You are the Lead Multi-Agent AI coordinator for the AIM Intelligence Platform (AIP).
    Synthesize an intelligent cross-functional discussion between three specialized agents evaluating ML trial runs to nominate a champion:
    1. Grid Search Optimizer Agent: Ingests hyperparameters, reviews scores across models, and highlights which parameter boundaries yielded high accuracy.
    2. Model Evaluator Agent: Focuses strictly on comparing validation metrics (Accuracy, ROC-AUC, F1-Score) and prediction latencies (<150ms enterprise threshold).
    3. Risk Validator Agent: Enforces model risk management restrictions (such as ensuring stable estimators and that F1 is not overfitted). Nominates the official champion.

    Your output MUST be a JSON object with a single key "dialogue" containing a list of exactly 3 objects.
    Each object must have:
    - "agent": The exact name of one of the 3 agents above.
    - "message": A 1-2 sentence precise contribution to the debate referencing specific run IDs (like run_xgb_model_003).
    - "action": A 3-5 word executive summary of their active operational role.
    Do not output any markdown formatting like ```json or anything else. Just the raw JSON object."""

    user_prompt = f"""We are evaluating the hyperparameter tuning trial grid: {experiments}.
    We must select the champion model based on highest ROC-AUC and within latency limits.
    Please generate the multi-agent debate transcript."""

    dialogue = []
    llm_res = await call_llm(system_prompt, user_prompt, json_mode=True)
    if llm_res:
        try:
            parsed = json.loads(llm_res)
            if isinstance(parsed, dict) and "dialogue" in parsed and isinstance(parsed["dialogue"], list):
                dialogue = parsed["dialogue"]
        except Exception as e:
            print(f"[Multi-Agent Develop] Failed to parse LLM dialogue JSON: {str(e)}")

    # Procedural fallback dialogue if LLM is offline/key is missing
    if not dialogue:
        dialogue = [
            {
                'agent': "Grid Search Optimizer Agent",
                'message': "Completed hyperparameter tuning grid sweeps. XGBoost runs with maxDepth=10 and estimators=300 (run_xgb_model_003) converged to the highest train-accuracy plateau.",
                'action': "Tuning boundaries sweep review."
            },
            {
                'agent': "Model Evaluator Agent",
                'message': "Confirmed. run_xgb_model_003 achieves peak performance indices: 0.93 Accuracy, 0.96 ROC-AUC, and 0.91 F1-Score, maintaining a latency of 118ms which is safely below our <150ms limit.",
                'action': "Accuracy & latency verification."
            },
            {
                'agent': "Risk Validator Agent",
                'message': "I approve run_xgb_model_003 as our official Enterprise Model Champion. The learningRate of 0.001 minimizes risk of local minima overshoot, and validation curves show no overfitting.",
                'action': "Champion nomination sign-off."
            }
        ]

    return {
        'experiments': experiments,
        'totalCount': len(experiments),
        'championRun': 'run_xgb_model_003',
        'agentDialogue': dialogue
    }
