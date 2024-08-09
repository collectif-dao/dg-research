from dataclasses import dataclass, field

from model.actors.actor import BaseActor, GovernanceParticipation, ReactionTime
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import ProposalStatus


@dataclass
class StHolderActor(BaseActor):
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def will_change_escrow(self, dg: DualGovernance):
        if self.reaction_time == ReactionTime.Slow:
            return 0

        if sum(1 for p in dg.timelock.proposals.state.proposals if p.status == ProposalStatus.Submitted) > 1:
            return self.st_eth_balance
        else:
            if self.address in dg.get_veto_signalling_escrow().accounting.state.assets:
                return -1 * self.st_eth_locked
            else:
                return 0
