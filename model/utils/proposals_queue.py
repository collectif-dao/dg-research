from typing import List
import datetime

from model.types.proposals import Proposal
from model import sys_params

monthly_timesteps = int(datetime.timedelta(days=30) / sys_params.sys_params["timedelta_tick"])


class ProposalQueueManager:
    def __init__(self):
        self.proposal_queue: List[Proposal] = []
        self.last_registration_timestep: int = -monthly_timesteps

    def append_proposal(self, proposal: Proposal):
        if proposal is not None:
            self.proposal_queue.append(proposal)

    def pop_proposals_for_registration(self, timestep) -> List[Proposal] | None:
        if (self.last_registration_timestep + monthly_timesteps <= timestep) and self.proposal_queue:
            self.last_registration_timestep = timestep
            proposal_queue = [proposal for proposal in self.proposal_queue]
            self.clear_queue()
            return proposal_queue
        return []

    def clear_queue(self):
        self.proposal_queue.clear()

    def count(self) -> int:
        return len(self.proposal_queue)
