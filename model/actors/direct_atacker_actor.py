from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict

from model.actors.actor import BaseActor, GovernanceParticipation
from model.actors.config import *
from model.proposals.proposals import ProposalType
from specs.dual_governance import DualGovernance
from specs.dual_governance.state import State
from specs.parameters import *


@dataclass
class DirectAtackerActor(BaseActor):
    governance_participation: GovernanceParticipation = field(default_factory=lambda: GovernanceParticipation.Full)

    def will_change_escrow(self, dg: DualGovernance, proposals_type: Dict[int, ProposalType]):
        rqs = dg.get_veto_signalling_escrow().get_rage_quit_support()
        current_state = dg.get_current_state()
        if (current_state == State.VetoSignalling) and (
            dg.get_veto_signalling_duration().value
            < timedelta(days=(system_parameters["dynamic_timelock_max_duration"] - 0.1)).total_seconds()
        ):
            if self.address in dg.get_veto_signalling_escrow().accounting.state.assets:
                try:
                    dg.get_veto_signalling_escrow().accounting.checkAssetsUnlockDelayPassed(
                        self.address, timedelta(hours=5).total_seconds()
                    )
                    return -1 * self.st_eth_locked
                except:
                    return 0

        else:
            if rqs < 5 * 1e16:
                return self.st_eth_balance
            else:
                return 0
