"""Modelos heurísticos (determinísticos) usados pelo provedor "stub".

Funcionam 100% offline e servem de:
- implementação padrão enquanto não há chave de API configurada;
- linha de base enviada aos LLMs reais (o modelo refina, não parte do zero);
- referência para comparar a qualidade de um modelo de ML treinado no futuro.

Todas as funções são puras: recebem dicionários e devolvem dicionários.
"""

from typing import Any

POSITIVE_WORDS = (
    "interessad", "aprovad", "fechar", "fechamos", "gostou", "gostaram", "ótimo", "otimo",
    "excelente", "satisfeit", "avançar", "avancar", "confirmad", "aceitou", "positiv", "elogi",
)
NEGATIVE_WORDS = (
    "caro", "cancel", "reclama", "atras", "insatisfeit", "problema", "desist", "concorrente",
    "sem orçamento", "sem orcamento", "não tem interesse", "nao tem interesse", "adiar", "adiou",
    "demora", "ruim",
)


def fmt_brl(value: float | int | None) -> str:
    value = float(value or 0)
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def text_sentiment(text: str) -> float:
    """Sentimento simples por palavras-chave: -1 (negativo) a 1 (positivo)."""
    lowered = text.lower()
    pos = sum(lowered.count(w) for w in POSITIVE_WORDS)
    neg = sum(lowered.count(w) for w in NEGATIVE_WORDS)
    if pos + neg == 0:
        return 0.0
    return round((pos - neg) / (pos + neg), 2)


# --------------------------------------------------------------------------- lead scoring
def lead_score(f: dict[str, Any]) -> dict[str, Any]:
    """Probabilidade de ganho (0–100) a partir das features de uma negociação aberta."""
    factors: list[dict[str, Any]] = []

    def add(feature: str, adjustment: float, description: str, value: Any) -> None:
        if adjustment:
            factors.append(
                {
                    "feature": feature,
                    "description": description,
                    "value": value,
                    "impact": round(_clamp(adjustment / 20, -1, 1), 2),
                    "_adj": adjustment,
                }
            )

    base = float(f.get("stage_default_probability", f.get("probability", 10)))

    days_contact = f.get("days_since_last_interaction")
    if days_contact is None:
        add("dias_sem_contato", -8, "Nenhuma interação registrada com o cliente", None)
    elif days_contact <= 7:
        add("dias_sem_contato", 6, "Contato recente (até 7 dias)", days_contact)
    elif days_contact <= 14:
        add("dias_sem_contato", 2, "Contato nas últimas duas semanas", days_contact)
    elif days_contact <= 30:
        add("dias_sem_contato", -4, "Mais de 2 semanas sem contato", days_contact)
    else:
        add("dias_sem_contato", -10, "Mais de 30 dias sem contato", days_contact)

    recent = f.get("interactions_last_30d", 0)
    if recent >= 5:
        add("interacoes_30d", 6, "Alto engajamento nos últimos 30 dias", recent)
    elif recent >= 2:
        add("interacoes_30d", 3, "Engajamento moderado nos últimos 30 dias", recent)
    elif recent == 0:
        add("interacoes_30d", -5, "Sem interações nos últimos 30 dias", recent)

    days_in_stage = f.get("days_in_stage", 0)
    if days_in_stage > 30:
        add("dias_na_etapa", -8, "Parada há mais de 30 dias na mesma etapa", days_in_stage)
    elif days_in_stage > 14:
        add("dias_na_etapa", -4, "Parada há mais de 14 dias na mesma etapa", days_in_stage)

    to_close = f.get("days_to_expected_close")
    if to_close is not None:
        if to_close < 0:
            add("prazo_fechamento", -10, "Data prevista de fechamento já passou", to_close)
        elif to_close <= 15 and f.get("stage") in ("proposta", "negociacao"):
            add("prazo_fechamento", 4, "Fechamento previsto para os próximos 15 dias", to_close)

    previous_wins = f.get("client_previous_won_deals", 0)
    if previous_wins:
        add("cliente_recorrente", min(8, 4 + previous_wins * 2), "Cliente já comprou antes", previous_wins)

    win_rate = f.get("owner_win_rate")
    if win_rate is not None and f.get("owner_closed_deals", 0) >= 3:
        add("taxa_ganho_vendedor", round((win_rate - 0.5) * 10, 1), "Histórico de conversão do vendedor", win_rate)

    source = f.get("lead_source")
    if source == "indicacao":
        add("origem_lead", 5, "Lead veio de indicação", source)
    elif source in ("prospeccao_ativa", "outro"):
        add("origem_lead", -2, "Lead de origem fria", source)

    regressions = f.get("stage_regressions", 0)
    if regressions:
        add("retrocessos", -min(10, regressions * 5), "Negociação já voltou de etapa", regressions)

    sentiment = f.get("avg_sentiment")
    if sentiment is not None:
        if sentiment > 0.3:
            add("sentimento", 5, "Conversas com tom positivo", sentiment)
        elif sentiment < -0.3:
            add("sentimento", -8, "Conversas com tom negativo", sentiment)

    score = round(_clamp(base + sum(x["_adj"] for x in factors), 1, 95), 1)

    data_points = (f.get("interactions_total", 0) >= 5) + (f.get("history_events", 0) >= 2) + (win_rate is not None)
    confidence = "alta" if data_points >= 3 else "media" if data_points >= 2 else "baixa"

    factors.sort(key=lambda x: abs(x["_adj"]), reverse=True)
    negatives = [x for x in factors if x["_adj"] < 0]
    recommendation = _recommendation_for(negatives[0]["feature"]) if negatives else (
        "Negociação saudável: mantenha a cadência de contato e conduza para o fechamento."
    )
    for item in factors:
        item.pop("_adj")
    return {"score": score, "confidence": confidence, "factors": factors, "recommendation": recommendation}


def _recommendation_for(feature: str) -> str:
    return {
        "dias_sem_contato": "Retome o contato ainda hoje (ligação ou WhatsApp) e agende um próximo passo concreto.",
        "interacoes_30d": "Aumente a frequência de contato: envie conteúdo útil e proponha uma reunião curta.",
        "dias_na_etapa": "Negociação travada: identifique a objeção principal e defina uma ação para destravar.",
        "prazo_fechamento": "Atualize a data prevista de fechamento com o cliente e revise o plano de ação.",
        "taxa_ganho_vendedor": "Considere apoio de um vendedor mais experiente nesta negociação.",
        "origem_lead": "Lead frio: reforce a qualificação (orçamento, decisor, necessidade e prazo).",
        "retrocessos": "Entenda por que a negociação retrocedeu antes de avançar novamente.",
        "sentimento": "O tom das conversas está negativo: trate as objeções antes de insistir na proposta.",
    }.get(feature, "Revise o plano de ação desta negociação.")


# --------------------------------------------------------------------------- resumo do cliente
def client_summary(ctx: dict[str, Any]) -> dict[str, Any]:
    client = ctx["client"]
    interactions: list[dict[str, Any]] = ctx.get("interactions", [])
    deals: list[dict[str, Any]] = ctx.get("deals", [])
    payments: dict[str, Any] = ctx.get("payments", {})
    days_contact = ctx.get("days_since_last_interaction")

    who = client["name"] + (f" ({client['company']})" if client.get("company") else "")
    parts = [
        f"{who} está com status {client['status_label']}, origem {client['lead_source_label']}, "
        f"cadastrado em {client['created_at']}."
    ]
    if interactions:
        last = interactions[0]
        parts.append(
            f"Há {ctx.get('interactions_total', len(interactions))} interação(ões) registradas; "
            f"a última foi {last['type_label'].lower()} em {last['occurred_at'][:10]}."
        )
    else:
        parts.append("Ainda não há interações registradas.")

    open_deals = [d for d in deals if d["stage"] not in ("fechado_ganho", "fechado_perdido")]
    won_deals = [d for d in deals if d["stage"] == "fechado_ganho"]
    if open_deals:
        total_open = sum(d["estimated_value"] for d in open_deals)
        parts.append(f"Possui {len(open_deals)} negociação(ões) em aberto somando {fmt_brl(total_open)}.")
    if won_deals:
        parts.append(f"Já fechou {len(won_deals)} negociação(ões) ({fmt_brl(sum(d['estimated_value'] for d in won_deals))}).")
    if payments:
        parts.append(
            f"Financeiro: {fmt_brl(payments.get('paid'))} recebidos, {fmt_brl(payments.get('outstanding'))} em aberto"
            + (f", dos quais {fmt_brl(payments.get('overdue'))} em atraso." if payments.get("overdue") else ".")
        )

    key_points = []
    for item in interactions[:5]:
        label = item.get("subject") or item["content"][:90] + ("…" if len(item["content"]) > 90 else "")
        key_points.append(f"{item['occurred_at'][:10]} · {item['type_label']}: {label}")

    sentiments = [i["sentiment"] for i in interactions if i.get("sentiment") is not None]
    if not sentiments:
        sentiments = [text_sentiment(f"{i.get('subject') or ''} {i['content']}") for i in interactions[:10]]
    avg = sum(sentiments) / len(sentiments) if sentiments else None
    sentiment = (
        "indefinido" if avg is None else "positivo" if avg > 0.2 else "negativo" if avg < -0.2 else "neutro"
    )

    risks: list[str] = []
    actions: list[str] = []
    if payments.get("overdue"):
        risks.append(f"Pagamentos em atraso: {fmt_brl(payments['overdue'])} ({payments.get('overdue_count', 0)} fatura(s)).")
        actions.append("Contatar o financeiro do cliente para regularizar as faturas vencidas.")
    if days_contact is None or days_contact > 30:
        risks.append("Mais de 30 dias sem contato." if days_contact else "Nenhum contato registrado.")
        actions.append("Agendar um contato de relacionamento nesta semana.")
    stalled = [d for d in open_deals if d.get("days_in_stage", 0) > 30]
    if stalled:
        risks.append(f"{len(stalled)} negociação(ões) parada(s) há mais de 30 dias na mesma etapa.")
        actions.append(f"Destravar a negociação \"{stalled[0]['title']}\" com uma proposta de próximo passo.")
    if sentiment == "negativo":
        risks.append("Tom recente das conversas é negativo.")
        actions.append("Entender as objeções do cliente antes de novas ofertas.")
    if open_deals and not actions:
        best = max(open_deals, key=lambda d: d["estimated_value"])
        actions.append(f"Avançar a negociação \"{best['title']}\" para a próxima etapa.")
    if won_deals and not open_deals:
        actions.append("Explorar venda adicional (upsell/cross-sell) com base no histórico de compras.")
    if not actions:
        actions.append("Qualificar o lead: confirmar necessidade, orçamento, decisor e prazo.")

    return {
        "summary": " ".join(parts),
        "key_points": key_points,
        "sentiment": sentiment,
        "risks": risks,
        "next_best_actions": actions[:4],
    }


# --------------------------------------------------------------------------- insights do funil
def commercial_insights(ctx: dict[str, Any]) -> dict[str, Any]:
    kpis = ctx["kpis"]
    previous = ctx.get("previous_kpis") or {}
    focus = set(ctx.get("focus", []))
    insights: list[dict[str, Any]] = []

    if "funil" in focus:
        conv = kpis["conversion_rate"]
        closed = kpis["won_deals_count"] + kpis["lost_deals_count"]
        if closed:
            severity = "critico" if conv < 0.15 else "atencao" if conv < 0.3 else "info"
            insights.append({
                "category": "funil",
                "title": f"Taxa de conversão de {conv * 100:.1f}%",
                "description": f"{kpis['won_deals_count']} ganhas e {kpis['lost_deals_count']} perdidas no período.",
                "severity": severity,
                "metric": "conversion_rate",
                "value": conv,
                "recommendation": None if severity == "info" else
                    "Revise a qualificação nas etapas iniciais e os motivos de perda mais frequentes.",
            })
        stages = [s for s in ctx.get("funnel", []) if s.get("conversion_from_previous") is not None]
        if stages:
            worst = min(stages, key=lambda s: s["conversion_from_previous"])
            if worst["conversion_from_previous"] < 0.6:
                insights.append({
                    "category": "funil",
                    "title": f"Gargalo na entrada de {worst['label']}",
                    "description": f"Só {worst['conversion_from_previous'] * 100:.0f}% das negociações chegam a esta etapa.",
                    "severity": "atencao",
                    "metric": "stage_conversion",
                    "value": worst["conversion_from_previous"],
                    "recommendation": "Mapeie as objeções da etapa anterior e crie um roteiro para superá-las.",
                })
        stalled = ctx.get("stalled_deals", {})
        if stalled.get("count"):
            insights.append({
                "category": "funil",
                "title": f"{stalled['count']} negociação(ões) parada(s)",
                "description": f"Sem mudança de etapa há mais de {stalled.get('threshold_days', 30)} dias.",
                "severity": "atencao",
                "metric": "stalled_deals",
                "value": stalled["count"],
                "recommendation": "Faça uma revisão de pipeline com os responsáveis esta semana.",
                "related_entity_ids": stalled.get("ids", []),
            })
        late = ctx.get("overdue_close_deals", {})
        if late.get("count"):
            insights.append({
                "category": "funil",
                "title": f"{late['count']} negociação(ões) com previsão vencida",
                "description": "A data prevista de fechamento já passou e elas continuam abertas.",
                "severity": "info",
                "metric": "overdue_close_date",
                "value": late["count"],
                "recommendation": "Atualize as previsões para manter o forecast confiável.",
                "related_entity_ids": late.get("ids", []),
            })

    if "inadimplencia" in focus:
        rate = kpis["delinquency_rate"]
        if kpis["overdue_amount"]:
            severity = "critico" if rate > 0.15 else "atencao" if rate > 0.05 else "info"
            top = ctx.get("top_overdue", [])
            insights.append({
                "category": "inadimplencia",
                "title": f"Inadimplência de {rate * 100:.1f}%",
                "description": f"{fmt_brl(kpis['overdue_amount'])} em atraso em {kpis['overdue_count']} fatura(s)"
                + (f"; maior atraso: {top[0]['client']['name']} ({top[0]['days_overdue']} dias)." if top else "."),
                "severity": severity,
                "metric": "delinquency_rate",
                "value": rate,
                "recommendation": "Priorize a cobrança das faturas mais antigas e ofereça Pix para pagamento imediato.",
                "related_entity_ids": [t["client"]["id"] for t in top],
            })
        else:
            insights.append({
                "category": "inadimplencia",
                "title": "Nenhuma fatura em atraso",
                "description": "A carteira está em dia.",
                "severity": "info",
                "metric": "delinquency_rate",
                "value": 0.0,
            })

    if "receita" in focus:
        prev_rev = previous.get("total_revenue") or 0
        rev = kpis["total_revenue"]
        if prev_rev:
            change = (rev - prev_rev) / prev_rev
            insights.append({
                "category": "receita",
                "title": f"Receita {'cresceu' if change >= 0 else 'caiu'} {abs(change) * 100:.1f}%",
                "description": f"{fmt_brl(rev)} no período contra {fmt_brl(prev_rev)} no período anterior.",
                "severity": "info" if change >= -0.1 else "atencao",
                "metric": "total_revenue",
                "value": rev,
            })
        insights.append({
            "category": "receita",
            "title": f"Pipeline ponderado de {fmt_brl(kpis['weighted_pipeline_value'])}",
            "description": f"{kpis['open_deals_count']} negociações abertas somando {fmt_brl(kpis['open_pipeline_value'])}.",
            "severity": "info",
            "metric": "weighted_pipeline_value",
            "value": kpis["weighted_pipeline_value"],
        })

    if "origem_leads" in focus:
        sources = [s for s in ctx.get("lead_sources", []) if s["clients_count"] >= 3]
        if sources:
            best = max(sources, key=lambda s: s["conversion_rate"])
            insights.append({
                "category": "origem_leads",
                "title": f"{best['label']} é a origem que mais converte",
                "description": f"{best['conversion_rate'] * 100:.0f}% dos clientes dessa origem fecharam negócio.",
                "severity": "info",
                "metric": "lead_source_conversion",
                "value": best["conversion_rate"],
                "recommendation": f"Considere investir mais em {best['label']}.",
            })

    critical = [i for i in insights if i["severity"] == "critico"]
    warning = [i for i in insights if i["severity"] == "atencao"]
    if critical:
        headline = f"Atenção imediata: {critical[0]['title'].lower()}."
    elif warning:
        headline = f"{len(warning)} ponto(s) de atenção no período; principal: {warning[0]['title'].lower()}."
    else:
        headline = "Operação comercial saudável no período analisado."
    return {"headline": headline, "insights": insights}
