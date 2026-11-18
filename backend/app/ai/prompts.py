"""Prompts versionados. Mude a versão ao alterar um prompt — ela entra no hash do cache
e fica gravada em ai_insights.prompt_version, permitindo comparar versões."""

import json
from typing import Any, Literal

AITask = Literal["client_summary", "lead_score", "insights"]

PROMPT_VERSIONS: dict[str, str] = {
    "client_summary": "v1",
    "lead_score": "v1",
    "insights": "v1",
}

_SYSTEM = (
    "Você é um analista comercial sênior de um CRM B2B brasileiro. "
    "Responda SEMPRE em português do Brasil e SOMENTE com um objeto JSON válido, sem markdown. "
    "Baseie-se exclusivamente nos dados fornecidos; não invente fatos, valores ou nomes."
)

_INSTRUCTIONS: dict[str, str] = {
    "client_summary": (
        "Resuma o relacionamento com o cliente a partir dos dados abaixo. Responda com o JSON:\n"
        '{"summary": "parágrafo de até 6 frases", "key_points": ["até 5 fatos relevantes"], '
        '"sentiment": "positivo|neutro|negativo|indefinido", "risks": ["riscos objetivos"], '
        '"next_best_actions": ["até 4 ações práticas, começando por verbo"]}'
    ),
    "lead_score": (
        "Estime a probabilidade (0 a 100) de esta negociação ser GANHA. Use as features e a "
        "linha de base heurística (heuristic_baseline) como ponto de partida, ajustando-a apenas "
        "com justificativa nos dados. Responda com o JSON:\n"
        '{"score": número, "confidence": "baixa|media|alta", '
        '"factors": [{"feature": "nome", "description": "explicação", "value": valor, "impact": -1 a 1}], '
        '"recommendation": "uma ação prática"}'
    ),
    "insights": (
        "Gere insights comerciais acionáveis sobre o período, apenas nas categorias listadas em "
        "'focus'. Responda com o JSON:\n"
        '{"headline": "frase-resumo", "insights": [{"category": "funil|inadimplencia|receita|origem_leads", '
        '"title": "título curto", "description": "explicação com números", '
        '"severity": "info|atencao|critico", "metric": "nome_da_metrica", "value": número, '
        '"recommendation": "ação prática", "related_entity_ids": ["uuids dos dados, se houver"]}]}'
    ),
}


def build_prompts(task: AITask, context: dict[str, Any]) -> tuple[str, str]:
    data = json.dumps(context, ensure_ascii=False, default=str, indent=1)
    return _SYSTEM, f"{_INSTRUCTIONS[task]}\n\nDADOS (JSON):\n{data}"
