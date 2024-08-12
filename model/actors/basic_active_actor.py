import random
from dataclasses import dataclass, field
from typing import Dict

from model.actors.actor import BaseActor, GovernanceParticipation, ReactionTime
from model.actors.config import *
from model.proposals.proposals import ProposalType
from specs.dual_governance import DualGovernance
from specs.dual_governance.proposals import ProposalStatus


@dataclass
class BasicActiveActor(BaseActor):
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def will_change_escrow(self, dg: DualGovernance, proposals_type: Dict[int, ProposalType]):
        danger_proposals_count = sum(
            1
            for p in dg.timelock.proposals.state.proposals
            if (p.status == ProposalStatus.Submitted or p.status == ProposalStatus.Scheduled)
            and proposals_type[p.id] == ProposalType.Danger
        )
        negative_proposals_count = sum(
            1
            for p in dg.timelock.proposals.state.proposals
            if (p.status == ProposalStatus.Submitted or p.status == ProposalStatus.Scheduled)
            and proposals_type[p.id] == ProposalType.Negative
        )

        danger_proposal_timestamp = 0
        if danger_proposals_count > 0:
            danger_proposal_timestamp = min(
                p.submittedAt.value
                for p in dg.timelock.proposals.state.proposals
                if (p.status == ProposalStatus.Submitted or p.status == ProposalStatus.Scheduled)
                and proposals_type[p.id] == ProposalType.Danger
            )
        negative_proposal_timestamp = 0
        if negative_proposals_count > 0:
            negative_proposal_timestamp = min(
                p.submittedAt.value
                for p in dg.timelock.proposals.state.proposals
                if (p.status == ProposalStatus.Submitted or p.status == ProposalStatus.Scheduled)
                and proposals_type[p.id] == ProposalType.Negative
            )

        if self.reaction_time == ReactionTime.Slow:
            reaction_delay = random.randint(normal_actor_max_delay, slow_actor_max_delay)
        elif self.reaction_time == ReactionTime.Normal:
            reaction_delay = random.randint(quick_actor_max_delay, normal_actor_max_delay)
        else:
            reaction_delay = random.randint(0, quick_actor_max_delay)

        if danger_proposals_count > 0 or negative_proposals_count > 2:
            if (
                max(negative_proposal_timestamp, danger_proposal_timestamp) + reaction_delay
                < dg.time_manager.get_current_timestamp_value().value
            ):
                return self.st_eth_balance
            else:
                return 0
        else:
            if self.address in dg.get_veto_signalling_escrow().accounting.state.assets:
                return -1 * self.st_eth_locked
            else:
                return 0
