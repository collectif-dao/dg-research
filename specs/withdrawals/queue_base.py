from dataclasses import dataclass, field
from typing import Dict, List

from specs.time_manager import TimeManager
from specs.types.timestamp import Timestamp
from specs.withdrawals.errors import Errors


@dataclass
class WithdrawalRequest:
    cumulative_stETH: int = field(default_factory=lambda: 0)
    cumulative_shares: int = field(default_factory=lambda: 0)
    owner: str = field(default_factory=lambda: "0x0000000000000000000000000000000000000000")
    timestamp: Timestamp = field(default_factory=lambda: Timestamp(0))
    claimed: bool = field(default_factory=lambda: False)
    report_timestamp: Timestamp = field(default_factory=lambda: Timestamp(0))


@dataclass
class Checkpoint:
    from_request_id: int = field(default_factory=lambda: 0)
    max_share_rate: int = field(default_factory=lambda: 0)


@dataclass
class WithdrawalRequestStatus:
    amount_of_stETH: int = field(default_factory=lambda: 0)
    amount_of_shares: int = field(default_factory=lambda: 0)
    owner: str = field(default_factory=lambda: "0x0000000000000000000000000000000000000000")
    timestamp: Timestamp = field(default_factory=lambda: 0)
    is_finalized: bool = field(default_factory=lambda: False)
    is_claimed: bool = field(default_factory=lambda: False)


class BatchesCalculationState:
    remaining_eth_budget: int
    finished: bool
    batches: List[int]
    batches_length: int


@dataclass
class WithdrawalQueueBase:
    MAX_BATCHES_LENGTH: int = 36
    E27_PRECISION_BASE: int = 10**27
    NOT_FOUND: int = 0

    time_manager: TimeManager = None

    queue: Dict[int, WithdrawalRequest] = field(default_factory=dict)
    last_request_id: int = field(default_factory=lambda: 0)
    last_finalized_request_id: int = field(default_factory=lambda: 0)
    checkpoints: Dict[int, Checkpoint] = field(default_factory=dict)
    last_checkpoint_index: int = field(default_factory=lambda: 0)
    locked_ether_amount: int = field(default_factory=lambda: 0)
    requests_by_owner: Dict[str, List[int]] = field(default_factory=dict)
    last_report_timestamp: Timestamp = field(default_factory=lambda: Timestamp(0))

    def _initialize_queue(self, time_manager: TimeManager):
        self.queue[0] = WithdrawalRequest(0, 0, "0x0000000000000000000000000000000000000000", 0, True, 0)
        self.checkpoints[self.last_checkpoint_index] = Checkpoint(0, 0)
        self.time_manager = time_manager

    ## ---
    ## external functions
    ## ---

    def calculate_finalization_batches(
        self, max_share_rate: int, max_timestamp: Timestamp, max_requests_per_call: int, state: BatchesCalculationState
    ) -> BatchesCalculationState:
        if state.finished or state.remaining_eth_budget == 0:
            raise Errors.InvalidState

        current_id = (
            self.last_finalized_request_id + 1
            if state.batches_length == 0
            else state.batches[state.batches_length - 1] + 1
        )
        prev_request = self.queue[current_id - 1]
        prev_request_share_rate = (
            self._calc_batch(self.queue[current_id - 2], prev_request)[0] if state.batches_length != 0 else 0
        )

        next_call_request_id = current_id + max_requests_per_call
        queue_length = self.last_request_id + 1

        while current_id < queue_length and current_id < next_call_request_id:
            request = self.queue[current_id]

            if request.timestamp > max_timestamp:
                break

            request_share_rate, eth_to_finalize, shares = self._calc_batch(prev_request, request)

            if request_share_rate > max_share_rate:
                eth_to_finalize = (shares * max_share_rate) // self.E27_PRECISION_BASE

            if eth_to_finalize > state.remaining_eth_budget:
                break

            state.remaining_eth_budget -= eth_to_finalize

            if state.batches_length != 0 and (
                prev_request.report_timestamp == request.report_timestamp
                or (prev_request_share_rate <= max_share_rate and request_share_rate <= max_share_rate)
                or (prev_request_share_rate > max_share_rate and request_share_rate > max_share_rate)
            ):
                state.batches[state.batches_length - 1] = current_id
            else:
                if state.batches_length == self.MAX_BATCHES_LENGTH:
                    break

                state.batches.append(current_id)
                state.batches_length += 1

            prev_request_share_rate = request_share_rate
            prev_request = request
            current_id += 1

        state.finished = current_id == queue_length or current_id < next_call_request_id
        return state

    def prefinalize(self, batches: List[int], max_share_rate: int) -> tuple[int, int]:
        if max_share_rate == 0:
            raise Errors.ZeroShareRate
        if not batches:
            raise Errors.EmptyBatches

        if batches[0] <= self.last_finalized_request_id:
            raise Errors.InvalidRequestId(batches[0])
        if batches[-1] > self.last_request_id:
            raise Errors.InvalidRequestId(batches[-1])

        eth_to_lock = 0
        shares_to_burn = 0
        prev_batch_end_request_id = self.last_finalized_request_id
        prev_batch_end = self.queue[prev_batch_end_request_id]

        for batch_end_request_id in batches:
            if batch_end_request_id <= prev_batch_end_request_id:
                raise Errors.BatchesAreNotSorted

            batch_end = self.queue[batch_end_request_id]
            batch_share_rate, stETH, shares = self._calc_batch(prev_batch_end, batch_end)

            if batch_share_rate > max_share_rate:
                eth_to_lock += (shares * max_share_rate) // self.E27_PRECISION_BASE
            else:
                eth_to_lock += stETH

            shares_to_burn += shares
            prev_batch_end_request_id = batch_end_request_id
            prev_batch_end = batch_end

        return eth_to_lock, shares_to_burn

    ## ---
    ## get queue base state
    ## ---

    def get_last_request_id(self) -> int:
        return self.last_request_id

    def get_last_finalized_request_id(self) -> int:
        return self.last_finalized_request_id

    def get_locked_ether_amount(self) -> int:
        return self.locked_ether_amount

    def get_last_checkpoint_index(self) -> int:
        return self.last_checkpoint_index

    def unfinalized_request_number(self) -> int:
        return self.last_request_id - self.last_finalized_request_id

    def unfinalized_stETH(self) -> int:
        return (
            self.queue[self.last_request_id].cumulative_stETH
            - self.queue[self.last_finalized_request_id].cumulative_stETH
        )

    ## ---
    ## internal methods
    ## ---

    def _finalize(self, last_request_id_to_be_finalized: int, amount_of_ETH: int, max_share_rate: int):
        if last_request_id_to_be_finalized > self.last_request_id:
            raise Errors.InvalidRequestId(last_request_id_to_be_finalized)
        if last_request_id_to_be_finalized <= self.last_finalized_request_id:
            raise Errors.InvalidRequestId(last_request_id_to_be_finalized)

        last_finalized_request = self.queue[self.last_finalized_request_id]
        request_to_finalize = self.queue[last_request_id_to_be_finalized]

        steth_to_finalize = request_to_finalize.cumulative_stETH - last_finalized_request.cumulative_stETH

        if amount_of_ETH > steth_to_finalize:
            raise Errors.TooMuchEtherToFinalize(amount_of_ETH, steth_to_finalize)

        first_request_id_to_finalize = self.last_finalized_request_id + 1
        self.checkpoints[self.last_checkpoint_index + 1] = Checkpoint(first_request_id_to_finalize, max_share_rate)
        self.last_checkpoint_index += 1

        self.locked_ether_amount += amount_of_ETH
        self.last_finalized_request_id = last_request_id_to_be_finalized

    def _enqueue(self, amount_of_stETH: int, amount_of_shares: int, owner: str) -> int:
        last_request_id = self.last_request_id
        lastRequest = self.queue[last_request_id]

        cumulative_shares = lastRequest.cumulative_shares + amount_of_shares
        cumulative_stETH = lastRequest.cumulative_stETH + amount_of_stETH

        request_id = last_request_id + 1
        self.last_request_id = request_id

        new_request = WithdrawalRequest(
            cumulative_stETH,
            cumulative_shares,
            owner,
            self.time_manager.get_current_timestamp_value(),
            False,
            self.last_report_timestamp,
        )

        self.queue[request_id] = new_request

        if owner not in self.requests_by_owner:
            self.requests_by_owner[owner] = []

        self.requests_by_owner[owner].append(request_id)

        return request_id

    def _get_status(self, request_id: int) -> WithdrawalRequestStatus:
        if request_id == 0 or request_id > self.last_request_id:
            raise Errors.InvalidRequestId(request_id)

        request = self.queue[request_id]
        prev_request = self.queue[request_id - 1]

        return WithdrawalRequestStatus(
            request.cumulative_stETH - prev_request.cumulative_stETH,
            request.cumulative_shares - prev_request.cumulative_shares,
            request.owner,
            request.timestamp,
            request_id <= self.last_finalized_request_id,
            request.claimed,
        )

    def _find_checkpoint_hint(self, request_id: int, start: int, end: int) -> int:
        if request_id == 0 or request_id > self.last_request_id:
            raise Errors.InvalidRequestId(request_id)

        if start == 0 or end > self.last_checkpoint_index:
            raise Errors.InvalidRequestIdRange(start, end)

        if self.last_checkpoint_index == 0 or request_id > self.last_finalized_request_id or start > end:
            return self.NOT_FOUND

        if request_id >= self.checkpoints[end].from_request_id:
            if end == self.last_checkpoint_index:
                return end

            if request_id < self.checkpoints[end + 1].from_request_id:
                return end

            return self.NOT_FOUND

        if request_id < self.checkpoints[start].from_request_id:
            return self.NOT_FOUND

        min_idx = start
        max_idx = end - 1

        while max_idx > min_idx:
            mid = (max_idx + min_idx + 1) // 2

            if self.checkpoints[mid].from_request_id <= request_id:
                min_idx = mid

            else:
                max_idx = mid - 1

        return min_idx

    def _claim(self, request_id: int, hint: int, recipient: str) -> int:
        if request_id == 0:
            raise Errors.InvalidRequestId(request_id)

        if request_id > self.last_finalized_request_id:
            raise Errors.RequestNotFoundOrNotFinalized(request_id)

        request = self.queue[request_id]

        if request.claimed:
            raise Errors.RequestAlreadyClaimed(request_id)
        if request.owner != recipient:
            raise Errors.NotOwner(recipient, request.owner)

        request.claimed = True
        self.requests_by_owner[request.owner].remove(request_id)

        eth_with_discount = self._calculate_claimable_ether(request, request_id, hint)

        if self.locked_ether_amount < eth_with_discount:
            raise Errors.NotEnoughEther

        self.locked_ether_amount -= eth_with_discount
        self._send_value(recipient, eth_with_discount)

        return eth_with_discount

    def _calculate_claimable_ether(self, request: WithdrawalRequest, request_id: int, hint: int) -> int:
        if hint == 0:
            raise Errors.InvalidHint(hint)

        if hint > self.last_checkpoint_index:
            raise Errors.InvalidHint(hint)

        checkpoint = self.checkpoints[hint]

        if request_id < checkpoint.from_request_id:
            raise Errors.InvalidHint(hint)

        if hint < self.last_checkpoint_index:
            next_checkpoint = self.checkpoints[hint + 1]

            if next_checkpoint.from_request_id <= request_id:
                raise Errors.InvalidHint(hint)

        prev_request = self.queue[request_id - 1]
        batch_share_rate, eth, shares = self._calc_batch(prev_request, request)

        if batch_share_rate > checkpoint.max_share_rate:
            eth = (shares * checkpoint.max_share_rate) // self.E27_PRECISION_BASE

        return eth

    def _send_value(self, recipient: str, amount: int):
        # Simulate sending value
        pass

    def _calc_batch(self, pre_start_request: WithdrawalRequest, end_request: WithdrawalRequest) -> tuple[int, int, int]:
        stETH = end_request.cumulative_stETH - pre_start_request.cumulative_stETH
        shares = end_request.cumulative_shares - pre_start_request.cumulative_shares
        share_rate = (stETH * self.E27_PRECISION_BASE) // shares

        return share_rate, stETH, shares
