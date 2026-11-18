# ULTRON Physics & Falsification Kernels
from .physics_kernels import (
    BenettinKernel,
    NumericalIntegrator,
    ThermodynamicKernel,
    PoincareSectionExtractor,
    RecurrenceAnalyzer,
    CorrelationDimension,
    classify_chaos,
    LyapunovResult,
    IntegrationResult,
    PoincareResult,
    RQAResult,
    ChaosReport
)
from .falsification_engine import (
    FalsificationEngine,
    FalsificationVerdict,
    FalsificationReport,
    FalsificationResult
)

# Semantic alias
PopperianFalsificationEngine = FalsificationEngine

__all__ = [
    'BenettinKernel',
    'NumericalIntegrator',
    'ThermodynamicKernel',
    'PoincareSectionExtractor',
    'RecurrenceAnalyzer',
    'CorrelationDimension',
    'classify_chaos',
    'LyapunovResult',
    'IntegrationResult',
    'PoincareResult',
    'RQAResult',
    'ChaosReport',
    'FalsificationEngine',
    'PopperianFalsificationEngine',
    'FalsificationVerdict',
    'FalsificationReport',
    'FalsificationResult'
]
