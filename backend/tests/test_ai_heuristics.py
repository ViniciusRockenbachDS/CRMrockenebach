from app.ai.heuristics import client_summary, commercial_insights, fmt_brl, lead_score, text_sentiment


def _features(**overrides):
    base = {
        "stage": "negociacao", "stage_default_probability": 75, "probability": 75,
        "days_since_last_interaction": 3, "interactions_last_30d": 6, "interactions_total": 8,
        "days_in_stage": 5, "days_to_expected_close": 10, "client_previous_won_deals": 1,
        "owner_win_rate": 0.6, "owner_closed_deals": 10, "lead_source": "indicacao",
        "stage_regressions": 0, "avg_sentiment": 0.5, "history_events": 4,
    }
    return {**base, **overrides}


def test_engaged_deal_scores_higher_than_cold_deal() -> None:
    hot = lead_score(_features())
    cold = lead_score(_features(days_since_last_interaction=60, interactions_last_30d=0, days_in_stage=45,
                                days_to_expected_close=-20, avg_sentiment=-0.6, client_previous_won_deals=0))
    assert 1 <= cold["score"] < hot["score"] <= 95
    assert hot["confidence"] == "alta"
    assert all(-1 <= f["impact"] <= 1 for f in cold["factors"])
    assert "contato" in cold["recommendation"].lower() or "prazo" in cold["recommendation"].lower() or cold["recommendation"]


def test_sentiment_and_currency() -> None:
    assert text_sentiment("Cliente aprovou e gostou muito") > 0
    assert text_sentiment("Achou caro e vai cancelar") < 0
    assert fmt_brl(1234.5) == "R$ 1.234,50"


def test_client_summary_flags_overdue() -> None:
    result = client_summary({
        "client": {"name": "Ana", "company": "ACME", "status_label": "Cliente", "lead_source_label": "Site",
                   "created_at": "2026-01-10"},
        "interactions": [],
        "deals": [],
        "payments": {"paid": 1000, "outstanding": 500, "overdue": 500, "overdue_count": 1},
        "days_since_last_interaction": None,
    })
    assert "ACME" in result["summary"]
    assert any("atraso" in r for r in result["risks"])
    assert result["next_best_actions"]


def test_insights_detect_delinquency() -> None:
    kpis = {
        "conversion_rate": 0.1, "won_deals_count": 1, "lost_deals_count": 9, "delinquency_rate": 0.2,
        "overdue_amount": 5000.0, "overdue_count": 2, "total_revenue": 10000.0,
        "weighted_pipeline_value": 20000.0, "open_deals_count": 5, "open_pipeline_value": 40000.0,
    }
    result = commercial_insights({"kpis": kpis, "focus": ["funil", "inadimplencia"], "funnel": [], "top_overdue": []})
    severities = {i["category"]: i["severity"] for i in result["insights"]}
    assert severities["inadimplencia"] == "critico"
    assert result["headline"].startswith("Atenção")
