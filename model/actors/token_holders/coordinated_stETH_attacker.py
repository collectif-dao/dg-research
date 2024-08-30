from dataclasses import dataclass, field
from typing import List, Tuple

from model.actors.actor import BaseActor
from model.types.actors import ActorType
from model.types.governance_participation import GovernanceParticipation
from model.types.proposals import Proposal
from specs.dual_governance import DualGovernance


@dataclass
class CoordinatedStETHAttackerActor(BaseActor):
    actor_type: ActorType = ActorType.CoordinatedAttacker
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def calculate_lock_amount(self, dual_governance: DualGovernance, proposals: List[Proposal]) -> Tuple[int, int]:
        return 0, 0

    def attack_honest_actors(self, proposal: Proposal, stETH_gain_per_attacker: int, wstETH_gain_per_attacker: int):
        self.hypothetical_stETH_balance = self.st_eth_balance + stETH_gain_per_attacker
        self.hypothetical_wstETH_balance = self.wstETH_balance + wstETH_gain_per_attacker
