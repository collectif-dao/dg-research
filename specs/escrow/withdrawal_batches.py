from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from specs.types.sequential_batches import SequentialBatch, SequentialBatches


class Status(Enum):
    Empty = 0
    Opened = 1
    Closed = 2


@dataclass
class QueueIndex:
    batch_index: int = field(default_factory=lambda: 0)
    value_index: int = field(default_factory=lambda: 0)


class InvalidWithdrawalsBatchesQueueStatus(Exception):
    pass


@dataclass
class State:
    status: Status = Status.Empty
    last_claimed_unstETH_id_index: QueueIndex = field(default_factory=QueueIndex)
    total_unstETH_count: int = field(default_factory=lambda: 0)
    total_unstETH_claimed: int = field(default_factory=lambda: 0)
    batches: list[SequentialBatch] = field(default_factory=list)


@dataclass
class WithdrawalsBatchesQueue:
    state: State = field(default_factory=lambda: State())

    def calc_request_amounts(self, min_request_amount: int, request_amount: int, amount: int) -> List[int]:
        requests_count = amount // request_amount

        last_request_amount = amount - requests_count * request_amount

        if last_request_amount >= min_request_amount:
            requests_count += 1

        request_amounts = [request_amount] * requests_count

        if last_request_amount >= min_request_amount:
            request_amounts[requests_count - 1] = last_request_amount

        return request_amounts

    def open(self):
        self._check_status(Status.Empty)

        self.state.batches.append(SequentialBatches.create(0, 1))
        self.state.status = Status.Opened

    def close(self):
        self._check_status(Status.Opened)
        self.state.status = Status.Closed

    def is_closed(self) -> bool:
        return self.state.status == Status.Closed

    def is_all_unstETH_claimed(self) -> bool:
        return self.state.total_unstETH_claimed == self.state.total_unstETH_count

    def check_opened(self):
        self._check_status(Status.Opened)

    def add(self, unstETH_ids: List[int]):
        unstETH_ids_count = len(unstETH_ids)
        if unstETH_ids_count == 0:
            return

        for i in range(unstETH_ids_count - 1):
            assert unstETH_ids[i + 1] == unstETH_ids[i] + 1

        last_batch_index = len(self.state.batches) - 1
        last_withdrawals_batch = self.state.batches[last_batch_index]
        new_withdrawals_batch = SequentialBatches.create(unstETH_ids[0], unstETH_ids_count)

        if SequentialBatches.can_merge(last_withdrawals_batch, new_withdrawals_batch):
            self.state.batches[last_batch_index] = SequentialBatches.merge(
                last_withdrawals_batch, new_withdrawals_batch
            )
        else:
            self.state.batches.append(new_withdrawals_batch)

        self.state.total_unstETH_count = self.state.total_unstETH_count + new_withdrawals_batch.size()

    def claim_next_batch(self, max_unstETH_ids_count: int) -> List[int]:
        unstETH_ids, self.state.last_claimed_unstETH_id_index = self._get_next_claimable_unstETH_ids(
            max_unstETH_ids_count
        )
        self.state.total_unstETH_claimed += len(unstETH_ids)

        return unstETH_ids

    def get_next_withdrawals_batches(self, limit: int) -> List[int]:
        unstETH_ids, _ = self._get_next_claimable_unstETH_ids(limit)
        return unstETH_ids

    def _get_next_claimable_unstETH_ids(self, max_unstETH_ids_count: int) -> Tuple[List[int], QueueIndex]:
        unstETH_ids_count = min(
            self.state.total_unstETH_count - self.state.total_unstETH_claimed, max_unstETH_ids_count
        )

        unstETH_ids = [0] * unstETH_ids_count
        last_claimed_unstETH_id_index = self.state.last_claimed_unstETH_id_index

        current_batch = self.state.batches[last_claimed_unstETH_id_index.batch_index]

        for i in range(unstETH_ids_count):
            last_claimed_unstETH_id_index.value_index += 1

            if current_batch.size() == last_claimed_unstETH_id_index.value_index:
                last_claimed_unstETH_id_index.batch_index += 1
                last_claimed_unstETH_id_index.value_index = 0

                current_batch = self.state.batches[last_claimed_unstETH_id_index.batch_index]

            unstETH_ids[i] = current_batch.value_at(last_claimed_unstETH_id_index.value_index)

        return unstETH_ids, last_claimed_unstETH_id_index

    def _check_status(self, expected_status: Status):
        if self.state.status != expected_status:
            raise InvalidWithdrawalsBatchesQueueStatus(self.state.status)
