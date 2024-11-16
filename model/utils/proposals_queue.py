from typing import List
from datetime import timedelta

from model.types.proposals import Proposal
from model.sys_params import sys_params

monthly_timesteps = int(timedelta(days=30) / sys_params["timedelta_tick"])


class ProposalQueueManager:
    def __init__(self):
        self.proposal_queue: List[Proposal] = []
        self.last_registration_timestep: int = -monthly_timesteps

    def append_proposal(self, proposal: Proposal):
        if proposal is not None:
            self.proposal_queue.append(proposal)

    def proposals_for_registration(self, timestep) -> List[Proposal] | None:
        if self.last_registration_timestep + monthly_timesteps <= timestep:
            if len(self.proposal_queue):
                self.last_registration_timestep = timestep
                return self.proposal_queue
            else:
                return None

        return None

    def clear_queue(self):
        self.proposal_queue.clear()

    def count(self) -> int:
        return len(self.proposal_queue)
