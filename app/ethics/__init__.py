"""
FreEco.ai Platform - Ethics Module
Enhanced OpenManus with comprehensive ethical framework
"""

from .ecological_principles import EcologicalSystem, default_ecological
from .freeco_laws import FreEcoBenchmark, FreEcoLawsEnforcer, default_freeco_laws


__all__ = [
    "FreEcoLawsEnforcer",
    "default_freeco_laws",
    "FreEcoBenchmark",
    "EcologicalSystem",
    "default_ecological",
]
