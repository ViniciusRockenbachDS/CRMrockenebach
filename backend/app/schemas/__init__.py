from app.schemas.ai import (
    AIInsightRead,
    AIMeta,
    AIStatus,
    BatchLeadScoreRequest,
    BatchLeadScoreResponse,
    ClientSummaryRequest,
    ClientSummaryResponse,
    Insight,
    InsightsRequest,
    InsightsResponse,
    LeadScoreFactor,
    LeadScoreRequest,
    LeadScoreResponse,
)
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenPair, TokenPayload
from app.schemas.client import (
    ClientCreate,
    ClientDetail,
    ClientFilters,
    ClientListItem,
    ClientRead,
    ClientStats,
    ClientUpdate,
)
from app.schemas.common import EnumOption, ErrorDetail, ErrorResponse, MessageResponse, Page, PaginationParams
from app.schemas.dashboard import (
    DashboardFilters,
    DashboardResponse,
    FunnelStageMetric,
    KPIComparison,
    KPISummary,
    LeadSourceMetric,
    OverduePaymentItem,
    RevenuePoint,
    TopClient,
)
from app.schemas.deal import (
    DealCreate,
    DealFilters,
    DealMove,
    DealRead,
    DealStageHistoryRead,
    DealUpdate,
    KanbanBoard,
    KanbanColumn,
)
from app.schemas.interaction import InteractionCreate, InteractionFilters, InteractionRead, InteractionUpdate
from app.schemas.payment import (
    PaymentCancel,
    PaymentCreate,
    PaymentFilters,
    PaymentInstallmentsCreate,
    PaymentMarkPaid,
    PaymentRead,
    PaymentUpdate,
    ReceivablesSummary,
)
from app.schemas.summaries import ClientSummary, DealSummary, UserSummary
from app.schemas.user import PasswordChange, UserCreate, UserRead, UserSelfUpdate, UserUpdate
