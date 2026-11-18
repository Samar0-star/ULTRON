"""
Epistemic Dossier Composer
===========================
Exports discovery dossier compilation components linking claims to proofs.
"""

from backend.core.epistemic_dossier import (
    EpistemicDossierGenerator,
    get_epistemic_dossier_generator,
    generate_discovery_dossier
)

class EpistemicDossierComposer:
    """
    High-level facade for composing verified epistemic dossiers.
    """
    def __init__(self, mission_id: str = "default_mission", title: str = "Epistemic Dossier"):
        self.mission_id = mission_id
        self.title = title
        self.generator = get_epistemic_dossier_generator()

    def compose(self, **kwargs):
        return generate_discovery_dossier(
            session_id=self.mission_id,
            mission_name=self.title,
            **kwargs
        )

__all__ = [
    "EpistemicDossierComposer",
    "EpistemicDossierGenerator",
    "get_epistemic_dossier_generator",
    "generate_discovery_dossier"
]
