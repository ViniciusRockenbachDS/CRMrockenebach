"""Cria o administrador inicial e, opcionalmente, dados de demonstração.

Uso (dentro de backend/, com o venv ativo):
    python -m app.scripts.seed            # só o administrador do .env
    python -m app.scripts.seed --demo     # administrador + equipe + clientes, negociações e pagamentos
"""

import argparse
import asyncio
import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.ai.heuristics import text_sentiment
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models import (
    Client,
    ClientStatus,
    Deal,
    DealStage,
    DealStageHistory,
    Interaction,
    InteractionDirection,
    InteractionType,
    LeadSource,
    Payment,
    PaymentMethod,
    PaymentStatus,
    User,
    UserRole,
)
from app.services.user_service import ensure_first_admin

rng = random.Random(42)
NOW = datetime.now(UTC)
TODAY = date.today()
DEMO_PASSWORD = "Demo@12345"

TEAM = [
    ("Marina Costa", "marina@crm.local", UserRole.MANAGER),
    ("Rafael Lima", "rafael@crm.local", UserRole.SALES),
    ("Juliana Alves", "juliana@crm.local", UserRole.SALES),
]
FIRST_NAMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "João",
               "Karina", "Lucas", "Mariana", "Nicolas", "Olívia", "Paulo", "Renata", "Samuel", "Tatiane", "Vinícius"]
LAST_NAMES = ["Silva", "Souza", "Oliveira", "Pereira", "Costa", "Rodrigues", "Almeida", "Nascimento", "Lima",
              "Araújo", "Fernandes", "Carvalho", "Gomes", "Martins", "Rocha", "Ribeiro", "Schmitt", "Kruger"]
COMPANIES = ["Metalúrgica Vale Norte", "Têxtil Bom Fio", "Construtora Horizonte", "Clínica Bem Viver",
             "Transportes Rota Sul", "Padaria Trigo de Ouro", "Agro Campo Verde", "Escola Saber+",
             "Moveis Ferraz", "Auto Peças Pioneiro", "Studio Criativo Lumi", "Farmácia Vida Plena",
             "Distribuidora Litoral", "Tech Nuvem Sistemas", "Hotel Mar Azul", "Academia Corpo Ativo",
             "Contabilidade Exata", "Mercado Bom Preço", "Plásticos Atlântico", "Odonto Sorriso"]
DEAL_TITLES = ["Implantação do sistema", "Licença anual", "Consultoria de processos", "Treinamento da equipe",
               "Projeto de automação", "Contrato de suporte", "Expansão de módulos", "Integração com ERP",
               "Plano Enterprise", "Migração de dados"]
TAGS = ["vip", "indústria", "varejo", "serviços", "saúde", "recorrente", "grande porte", "pme"]
LOST_REASONS = ["Preço acima do orçamento", "Escolheu concorrente", "Projeto adiado", "Sem retorno do decisor"]
INTERACTIONS = [
    (InteractionType.LIGACAO, "Primeiro contato", "Cliente demonstrou interesse e pediu uma apresentação da solução."),
    (InteractionType.REUNIAO, "Apresentação", "Reunião ótima, a diretoria gostou e quer avançar para a proposta."),
    (InteractionType.EMAIL, "Envio de proposta", "Proposta comercial enviada com condições de pagamento em 3x."),
    (InteractionType.WHATSAPP, "Follow-up", "Cliente confirmou que está analisando internamente e retorna na semana."),
    (InteractionType.LIGACAO, "Negociação de valores", "Cliente achou caro e pediu desconto; vai comparar com concorrente."),
    (InteractionType.WHATSAPP, "Retorno do cliente", "Cliente aprovou a proposta e quer fechar ainda este mês."),
    (InteractionType.VISITA, "Visita técnica", "Visita realizada, levantamos os requisitos e o time está satisfeito."),
    (InteractionType.EMAIL, "Cobrança", "Enviado lembrete de fatura em atraso; cliente relatou problema no fluxo de caixa."),
    (InteractionType.NOTA, "Observação interna", "Decisor é o diretor financeiro; reunião só às quintas-feiras."),
    (InteractionType.LIGACAO, "Sem retorno", "Tentativa de contato sem sucesso; cliente pediu para adiar a conversa."),
]
OPEN_FLOW = [DealStage.PROSPECCAO, DealStage.QUALIFICACAO, DealStage.PROPOSTA, DealStage.NEGOCIACAO]


def _phone() -> str:
    return f"+55479{rng.randint(10000000, 99999999)}"


def _days_ago(days: float) -> datetime:
    return NOW - timedelta(days=days)


async def create_team(db) -> list[User]:
    users: list[User] = []
    for name, email, role in TEAM:
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(name=name, email=email, hashed_password=hash_password(DEMO_PASSWORD), role=role)
            db.add(user)
        users.append(user)
    await db.flush()
    return users


def build_deal(client: Client, owner: User, created: datetime, final_stage: DealStage) -> tuple[Deal, list[DealStageHistory]]:
    value = Decimal(rng.choice([3500, 4800, 7200, 9900, 12500, 18000, 24000, 36000, 52000])) + Decimal(rng.choice([0, 90, 450]))
    path = OPEN_FLOW[: (OPEN_FLOW.index(final_stage) + 1 if final_stage in OPEN_FLOW else rng.randint(2, 4))]
    if final_stage.is_closed:
        path = [*path, final_stage]

    # Distribui as mudanças de etapa entre a criação e hoje.
    span = max(1.0, (NOW - created).total_seconds() / 86400 - 1)
    moments = sorted(created + timedelta(days=rng.uniform(0, span)) for _ in path[1:])
    timeline = [created, *moments]

    deal = Deal(
        client_id=client.id, owner_id=owner.id, title=f"{rng.choice(DEAL_TITLES)} — {client.company or client.name}",
        description="Oportunidade gerada pelos dados de demonstração.", estimated_value=value,
        stage=final_stage, probability=final_stage.default_probability, stage_changed_at=timeline[-1],
        expected_close_date=(timeline[-1] + timedelta(days=rng.randint(-10, 45))).date(),
        closed_at=timeline[-1] if final_stage.is_closed else None,
        lost_reason=rng.choice(LOST_REASONS) if final_stage == DealStage.FECHADO_PERDIDO else None,
        created_at=created, updated_at=timeline[-1],
    )
    history: list[DealStageHistory] = []
    previous: DealStage | None = None
    for i, stage in enumerate(path):
        history.append(
            DealStageHistory(
                from_stage=previous, to_stage=stage, changed_by_id=owner.id, changed_at=timeline[i],
                estimated_value_snapshot=value, probability_snapshot=stage.default_probability,
                seconds_in_previous_stage=int((timeline[i] - timeline[i - 1]).total_seconds()) if i else None,
                note="Negociação criada" if i == 0 else None,
            )
        )
        previous = stage
    return deal, history


def build_payments(deal: Deal) -> list[Payment]:
    installments = rng.choice([1, 1, 2, 3])
    base = (deal.estimated_value / installments).quantize(Decimal("0.01"))
    first_due = (deal.closed_at or NOW).date() + timedelta(days=15)
    payments = []
    for n in range(installments):
        due = first_due + timedelta(days=30 * n)
        amount = base if n < installments - 1 else deal.estimated_value - base * (installments - 1)
        if due < TODAY:
            # 80% pagos (alguns com atraso), 20% inadimplentes
            if rng.random() < 0.8:
                status, paid = PaymentStatus.PAGO, min(TODAY, due + timedelta(days=rng.choice([0, 0, 2, 7])))
            else:
                status, paid = PaymentStatus.ATRASADO, None
        else:
            status, paid = PaymentStatus.PENDENTE, None
        payments.append(
            Payment(
                deal_id=deal.id, description=f"Parcela {n + 1}/{installments}", amount=amount,
                method=rng.choice(list(PaymentMethod)[:5]), status=status, due_date=due, payment_date=paid,
                installment_number=n + 1, installment_total=installments,
            )
        )
    return payments


async def create_demo_data(db, team: list[User]) -> None:
    sellers = team[1:]
    stage_weights = [
        (DealStage.PROSPECCAO, 3), (DealStage.QUALIFICACAO, 3), (DealStage.PROPOSTA, 3),
        (DealStage.NEGOCIACAO, 2), (DealStage.FECHADO_GANHO, 5), (DealStage.FECHADO_PERDIDO, 3),
    ]
    stages, weights = zip(*stage_weights, strict=True)
    positions: dict[DealStage, int] = {s: 0 for s in DealStage}

    for i in range(30):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        company = COMPANIES[i % len(COMPANIES)] + ("" if i < len(COMPANIES) else " Filial")
        created = _days_ago(rng.uniform(20, 200))
        owner = rng.choice(sellers)
        client = Client(
            name=name, company=company, job_title=rng.choice(["Diretor", "Gerente", "Sócio", "Compras"]),
            email=f"{name.split()[0].lower()}.{i}@exemplo.com.br", phone=_phone(),
            lead_source=rng.choice(list(LeadSource)), status=ClientStatus.LEAD,
            tags=rng.sample(TAGS, k=rng.randint(0, 2)), owner_id=owner.id, created_at=created, updated_at=created,
        )
        client.whatsapp = client.phone
        db.add(client)
        await db.flush()

        # Interações
        last_contact = None
        for _ in range(rng.randint(0, 6)):
            kind, subject, content = rng.choice(INTERACTIONS)
            when = created + timedelta(days=rng.uniform(0, max(1, (NOW - created).days)))
            db.add(
                Interaction(
                    client_id=client.id, user_id=owner.id, type=kind, subject=subject, content=content,
                    direction=InteractionDirection.INTERNA if kind == InteractionType.NOTA else InteractionDirection.SAIDA,
                    occurred_at=when, sentiment=Decimal(str(text_sentiment(content))),
                    duration_minutes=rng.choice([None, 10, 20, 45]) if kind in (InteractionType.LIGACAO, InteractionType.REUNIAO) else None,
                )
            )
            last_contact = max(last_contact or when, when)
        client.last_interaction_at = last_contact

        # Negociações
        statuses = set()
        for _ in range(rng.choice([0, 1, 1, 1, 2, 2, 3])):
            final_stage = rng.choices(stages, weights=weights)[0]
            deal_created = created + timedelta(days=rng.uniform(0, max(1, (NOW - created).days * 0.6)))
            deal, history = build_deal(client, owner, deal_created, final_stage)
            deal.position = positions[final_stage]
            positions[final_stage] += 1
            db.add(deal)
            await db.flush()
            for h in history:
                h.deal_id = deal.id
                db.add(h)
            if final_stage == DealStage.FECHADO_GANHO:
                for payment in build_payments(deal):
                    db.add(payment)
            statuses.add(final_stage)

        if DealStage.FECHADO_GANHO in statuses:
            client.status = ClientStatus.CLIENTE
        elif statuses & set(OPEN_FLOW):
            client.status = ClientStatus.PROSPECT
        elif statuses:
            client.status = ClientStatus.PERDIDO
    await db.commit()


async def main(demo: bool) -> None:
    async with AsyncSessionLocal() as db:
        admin = await ensure_first_admin(db)
        print(f"[ok] Administrador: {admin.email}")
        if demo:
            if await db.scalar(select(func.count()).select_from(Client)):
                print("[info] Já existem clientes no banco — dados de demonstração não foram recriados.")
            else:
                team = await create_team(db)
                await create_demo_data(db, team)
                print(f"[ok] Dados de demonstração criados. Equipe: {', '.join(e for _, e, _ in TEAM)} (senha {DEMO_PASSWORD})")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed do CRM")
    parser.add_argument("--demo", action="store_true", help="Cria equipe, clientes, negociações e pagamentos fictícios")
    asyncio.run(main(parser.parse_args().demo))
