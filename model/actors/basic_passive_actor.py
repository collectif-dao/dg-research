from dataclasses import dataclass, field
from typing import Dict

from model.actors.actor import BaseActor, GovernanceParticipation
from model.actors.config import *
from model.proposals.proposals import ProposalType
from specs.dual_governance import DualGovernance


@dataclass
class BasicActiveActor(BaseActor):
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def will_change_escrow(self, dg: DualGovernance, proposals_type: Dict[int, ProposalType]):
        return 0
