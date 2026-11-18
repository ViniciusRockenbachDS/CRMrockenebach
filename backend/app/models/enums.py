"""Enumerações de domínio.

Os VALORES (snake_case, sem acento) são o que vai para o banco e para a API.
Os RÓTULOS (`.label`) são o texto exibido na interface em português.
"""

from enum import StrEnum


class _LabeledEnum(StrEnum):
    @property
    def label(self) -> str:
        return _LABELS.get(type(self), {}).get(self.value, self.value)


class UserRole(_LabeledEnum):
    ADMIN = "admin"
    MANAGER = "gestor"
    SALES = "vendedor"


class LeadSource(_LabeledEnum):
    SITE = "site"
    INDICACAO = "indicacao"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"
    GOOGLE_ADS = "google_ads"
    EVENTO = "evento"
    PROSPECCAO_ATIVA = "prospeccao_ativa"
    OUTRO = "outro"


class ClientStatus(_LabeledEnum):
    LEAD = "lead"
    PROSPECT = "prospect"
    CLIENTE = "cliente"
    INATIVO = "inativo"
    PERDIDO = "perdido"


class InteractionType(_LabeledEnum):
    LIGACAO = "ligacao"
    EMAIL = "email"
    REUNIAO = "reuniao"
    WHATSAPP = "whatsapp"
    VISITA = "visita"
    NOTA = "nota"
    OUTRO = "outro"


class InteractionDirection(_LabeledEnum):
    ENTRADA = "entrada"   # cliente → empresa
    SAIDA = "saida"       # empresa → cliente
    INTERNA = "interna"   # anotação interna da equipe


class DealStage(_LabeledEnum):
    PROSPECCAO = "prospeccao"
    QUALIFICACAO = "qualificacao"
    PROPOSTA = "proposta"
    NEGOCIACAO = "negociacao"
    FECHADO_GANHO = "fechado_ganho"
    FECHADO_PERDIDO = "fechado_perdido"

    @property
    def is_closed(self) -> bool:
        return self in (DealStage.FECHADO_GANHO, DealStage.FECHADO_PERDIDO)

    @property
    def order(self) -> int:
        """Posição da etapa no funil (usada para ordenar colunas do Kanban)."""
        return list(DealStage).index(self)

    @property
    def default_probability(self) -> int:
        """Probabilidade sugerida ao entrar na etapa (pode ser ajustada manualmente ou pela IA)."""
        return _DEFAULT_PROBABILITY[self]

    @classmethod
    def open_stages(cls) -> tuple["DealStage", ...]:
        return tuple(s for s in cls if not s.is_closed)


class PaymentStatus(_LabeledEnum):
    PENDENTE = "pendente"
    PAGO = "pago"
    ATRASADO = "atrasado"
    CANCELADO = "cancelado"

    @property
    def is_receivable(self) -> bool:
        """Conta como 'a receber' (ainda em aberto)."""
        return self in (PaymentStatus.PENDENTE, PaymentStatus.ATRASADO)


class PaymentMethod(_LabeledEnum):
    PIX = "pix"
    BOLETO = "boleto"
    CARTAO_CREDITO = "cartao_credito"
    CARTAO_DEBITO = "cartao_debito"
    TRANSFERENCIA = "transferencia"
    DINHEIRO = "dinheiro"
    OUTRO = "outro"


class AuditAction(_LabeledEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    STAGE_CHANGE = "stage_change"
    STATUS_CHANGE = "status_change"
    LOGIN = "login"


class AIInsightType(_LabeledEnum):
    CLIENT_SUMMARY = "client_summary"
    LEAD_SCORE = "lead_score"
    FUNNEL_INSIGHT = "funnel_insight"
    DELINQUENCY_INSIGHT = "delinquency_insight"


_DEFAULT_PROBABILITY: dict[DealStage, int] = {
    DealStage.PROSPECCAO: 10,
    DealStage.QUALIFICACAO: 25,
    DealStage.PROPOSTA: 50,
    DealStage.NEGOCIACAO: 75,
    DealStage.FECHADO_GANHO: 100,
    DealStage.FECHADO_PERDIDO: 0,
}

# Rótulos indexados pela CLASSE do enum: valores iguais em enums diferentes
# (ex.: 'outro', 'whatsapp') não colidem, já que membros StrEnum têm o hash da string.
_LABELS: dict[type[StrEnum], dict[str, str]] = {
    UserRole: {
        UserRole.ADMIN.value: "Administrador",
        UserRole.MANAGER.value: "Gestor",
        UserRole.SALES.value: "Vendedor",
    },
    LeadSource: {
        LeadSource.SITE.value: "Site",
        LeadSource.INDICACAO.value: "Indicação",
        LeadSource.INSTAGRAM.value: "Instagram",
        LeadSource.FACEBOOK.value: "Facebook",
        LeadSource.LINKEDIN.value: "LinkedIn",
        LeadSource.WHATSAPP.value: "WhatsApp",
        LeadSource.GOOGLE_ADS.value: "Google Ads",
        LeadSource.EVENTO.value: "Evento",
        LeadSource.PROSPECCAO_ATIVA.value: "Prospecção ativa",
        LeadSource.OUTRO.value: "Outro",
    },
    ClientStatus: {
        ClientStatus.LEAD.value: "Lead",
        ClientStatus.PROSPECT.value: "Prospect",
        ClientStatus.CLIENTE.value: "Cliente",
        ClientStatus.INATIVO.value: "Inativo",
        ClientStatus.PERDIDO.value: "Perdido",
    },
    InteractionType: {
        InteractionType.LIGACAO.value: "Ligação",
        InteractionType.EMAIL.value: "E-mail",
        InteractionType.REUNIAO.value: "Reunião",
        InteractionType.WHATSAPP.value: "WhatsApp",
        InteractionType.VISITA.value: "Visita",
        InteractionType.NOTA.value: "Nota",
        InteractionType.OUTRO.value: "Outro",
    },
    InteractionDirection: {
        InteractionDirection.ENTRADA.value: "Entrada",
        InteractionDirection.SAIDA.value: "Saída",
        InteractionDirection.INTERNA.value: "Interna",
    },
    DealStage: {
        DealStage.PROSPECCAO.value: "Prospecção",
        DealStage.QUALIFICACAO.value: "Qualificação",
        DealStage.PROPOSTA.value: "Proposta",
        DealStage.NEGOCIACAO.value: "Negociação",
        DealStage.FECHADO_GANHO.value: "Fechado Ganho",
        DealStage.FECHADO_PERDIDO.value: "Fechado Perdido",
    },
    PaymentStatus: {
        PaymentStatus.PENDENTE.value: "Pendente",
        PaymentStatus.PAGO.value: "Pago",
        PaymentStatus.ATRASADO.value: "Atrasado",
        PaymentStatus.CANCELADO.value: "Cancelado",
    },
    PaymentMethod: {
        PaymentMethod.PIX.value: "Pix",
        PaymentMethod.BOLETO.value: "Boleto",
        PaymentMethod.CARTAO_CREDITO.value: "Cartão de crédito",
        PaymentMethod.CARTAO_DEBITO.value: "Cartão de débito",
        PaymentMethod.TRANSFERENCIA.value: "Transferência",
        PaymentMethod.DINHEIRO.value: "Dinheiro",
        PaymentMethod.OUTRO.value: "Outro",
    },
    AuditAction: {
        AuditAction.CREATE.value: "Criação",
        AuditAction.UPDATE.value: "Atualização",
        AuditAction.DELETE.value: "Exclusão",
        AuditAction.RESTORE.value: "Restauração",
        AuditAction.STAGE_CHANGE.value: "Mudança de etapa",
        AuditAction.STATUS_CHANGE.value: "Mudança de status",
        AuditAction.LOGIN.value: "Login",
    },
    AIInsightType: {
        AIInsightType.CLIENT_SUMMARY.value: "Resumo do cliente",
        AIInsightType.LEAD_SCORE.value: "Lead scoring",
        AIInsightType.FUNNEL_INSIGHT.value: "Insight do funil",
        AIInsightType.DELINQUENCY_INSIGHT.value: "Insight de inadimplência",
    },
}
