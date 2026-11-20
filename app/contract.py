from app.modules.m1_sampling.handler import router as sampling_router
from app.modules.m1_sampling.rules import run as sampling
from app.modules.m2_mapping.handler import router as mapping_router
from app.modules.m2_mapping.rules import run as mapping
from app.modules.m3_alignment.handler import router as alignment_router
from app.modules.m3_alignment.rules import run as alignment
from app.modules.m4_peak.handler import router as peak_router
from app.modules.m4_peak.rules import run as peak
from app.modules.m5_allocation.handler import router as allocation_router
from app.modules.m5_allocation.rules import run as allocation
from app.modules.m6_balance.handler import router as balance_router
from app.modules.m6_balance.rules import run as balance
from app.modules.m7_billing.handler import router as billing_router
from app.modules.m7_billing.rules import run as billing

TABLES = ("gateways", "readings", "mappings")
HOME = "peak"
STAGES = (
    ("sampling", "网关取样", sampling, sampling_router),
    ("mapping", "分表映射", mapping, mapping_router),
    ("alignment", "需量齐时", alignment, alignment_router),
    ("peak", "园区找峰", peak, peak_router),
    ("allocation", "住户分摊", allocation, allocation_router),
    ("balance", "功率勾稽", balance, balance_router),
    ("billing", "账单证据", billing, billing_router),
)
