# SVEL Epistemic Governance & Falsification
from .epistemic_regulator import EpistemicRegulator
from .the_morgue import TheMorgue, MorgueRecord, KillGate

try:
    from .dossier_composer import EpistemicDossierComposer
except ImportError:
    EpistemicDossierComposer = None

__all__ = [
    'EpistemicRegulator', 'TheMorgue',
    'MorgueRecord', 'KillGate', 'EpistemicDossierComposer'
]
