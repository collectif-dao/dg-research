from dataclasses import dataclass, field
from typing import Dict, List

from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.types.timestamp import Timestamp, Timestamps
from specs.withdrawals.errors import Errors
from specs.withdrawals.pausable import Pausable
from specs.withdrawals.queue_base import WithdrawalQueueBase, WithdrawalRequestStatus


@dataclass
class PermitInput:
    value: int
    deadline: int
    v: int
    r: str
    s: str


@dataclass
class WithdrawalQueue(WithdrawalQueueBase, Pausable):
    BUNKER_MODE_DISABLED_TIMESTAMP: Timestamp = Timestamps.MAX
    MIN_STETH_WITHDRAWAL_AMOUNT: int = 100
    MAX_STETH_WITHDRAWAL_AMOUNT: int = 1000 * 10**18

    time_manager: TimeManager = None
    lido: Lido = None

    address: str = Address.ZERO

    bunker_mode_since_timestamp: Timestamp = BUNKER_MODE_DISABLED_TIMESTAMP
    requests_by_owner: Dict[str, List[int]] = field(default_factory=dict)

    def initialize(self, time_manager: TimeManager, lido: Lido, address: str):
        self._initialize_queue(time_manager)
        self._pause_for(self.pause_infinite)

        self.time_manager = time_manager
        self.lido = lido
        self.address = address

    ## ---
    ## withdrawals functions
    ## ---

    def request_withdrawals(self, holder_addr: str, amounts: List[int], owner: str = Address.ZERO) -> List[int]:
        self._check_resumed()

        if owner == Address.ZERO:
            owner = holder_addr

        request_ids = []

        for amount in amounts:
            self._check_withdrawal_request_amount(amount)
            request_ids.append(self._request_withdrawal(holder_addr, amount, owner))

        return request_ids

    def request_withdrawals_wsteth(self, holder_addr: str, amounts: List[int], owner: str = Address.ZERO) -> List[int]:
        self._check_resumed()

        if owner == Address.ZERO:
            owner = holder_addr

        request_ids = []

        for amount in amounts:
            request_ids.append(self._request_withdrawal_wsteth(holder_addr, amount, owner))

        return request_ids

    def request_withdrawals_with_permit(
        self, holder_addr: str, amounts: List[int], owner: str, permit: PermitInput
    ) -> List[int]:
        self.lido.permit(holder_addr, self.address, permit.value, permit.deadline, permit.v, permit.r, permit.s)

        return self.request_withdrawals(holder_addr, amounts, owner)

    def request_withdrawals_wsteth_with_permit(
        self, holder_addr: str, amounts: List[int], owner: str, permit: PermitInput
    ) -> List[int]:
        self.lido.wstETH_permit(holder_addr, self.address, permit.value, permit.deadline, permit.v, permit.r, permit.s)

        return self.request_withdrawals_wsteth(holder_addr, amounts, owner)

    ## ---
    ## getters
    ## ---

    def get_withdrawal_requests(self, owner: str) -> List[int]:
        return self.requests_by_owner[owner]

    def get_withdrawal_status(self, request_ids: List[int]) -> List[WithdrawalRequestStatus]:
        statuses = []

        for request_id in request_ids:
            statuses.append(self._get_status(request_id))

        return statuses

    def get_claimable_ether(self, request_ids: List[int], hints: List[int]) -> List[int]:
        claimable_eth_values = []

        for i in range(len(request_ids)):
            claimable_eth_values.append(self._get_claimable_ether(request_ids[i], hints[i]))

        return claimable_eth_values

    ## ---
    ## claims section
    ## ---

    def claim_withdrawals_to(self, request_ids: List[int], hints: List[int], _recipient: str):
        if _recipient == Address.ZERO:
            raise Errors.ZeroRecipient

        if len(request_ids) != len(hints):
            raise Errors.ArraysLengthMismatch(len(request_ids), len(hints))

        for i in range(len(request_ids)):
            self._claim(request_ids[i], hints[i], _recipient)

    def claim_withdrawals(self, holder_addr: str, request_ids: List[int], hints: List[int]) -> int:
        if len(request_ids) != len(hints):
            raise Errors.ArraysLengthMismatch(len(request_ids), len(hints))

        total_claimed: int = 0

        for i in range(len(request_ids)):
            claimed = self._claim(request_ids[i], hints[i], holder_addr)
            total_claimed += claimed

        return total_claimed

    def claim_withdrawal(self, holder_addr: str, request_id: int):
        self._claim(
            request_id, self._find_checkpoint_hint(request_id, 1, self.get_last_checkpoint_index()), holder_addr
        )

    ## ---
    ## checkpoints
    ## ---

    def find_checkpoint_hints(self, request_ids: List[int], first_index: int, last_index: int) -> List[int]:
        hint_ids = []
        prev_request_id = 0

        for request_id in request_ids:
            if request_id < prev_request_id:
                raise Errors.RequestIdsNotSorted

            hint_ids.append(self._find_checkpoint_hint(request_id, first_index, last_index))
            first_index = hint_ids[-1]
            prev_request_id = request_id

        return hint_ids

    ## ---
    ## oracle report
    ## ---

    def on_oracle_report(
        self, is_bunker_mode_now: bool, bunker_start_timestamp: Timestamp, current_report_timestamp: Timestamp
    ):
        if bunker_start_timestamp >= self.time_manager.get_current_timestamp_value():
            raise Errors.InvalidReportTimestamp

        if current_report_timestamp >= self.time_manager.get_current_timestamp_value():
            raise Errors.InvalidReportTimestamp

        super().last_report_timestamp = current_report_timestamp

        is_bunker_mode_was_set_before = self.is_bunker_mode_active()

        if is_bunker_mode_now != is_bunker_mode_was_set_before:
            if is_bunker_mode_now:
                self.bunker_mode_since_timestamp = bunker_start_timestamp
            else:
                self.bunker_mode_since_timestamp = self.BUNKER_MODE_DISABLED_TIMESTAMP

    def is_bunker_mode_active(self) -> bool:
        return self.bunker_mode_since_timestamp < self.BUNKER_MODE_DISABLED_TIMESTAMP

    ## ---
    ## internal methods
    ## ---

    def _request_withdrawal(self, holder_addr: str, amount_of_steth: int, owner: str) -> int:
        self.lido.transferSharesFrom(holder_addr, self.address, self.address, amount_of_steth)

        amount_of_shares = self.lido.get_shares_by_pooled_eth(amount_of_steth)

        request_id = self._enqueue(int(amount_of_steth), int(amount_of_shares), owner)

        return request_id

    def _request_withdrawal_wsteth(self, holder_addr: str, amount_of_wsteth: int, owner: str) -> int:
        self.lido.wstETH_transferFrom(holder_addr, self.address, self.address, amount_of_wsteth)

        amount_of_steth = self.lido.unwrap(self.address, amount_of_wsteth)
        self._check_withdrawal_request_amount(amount_of_steth)

        amount_of_shares = self.lido.get_shares_by_pooled_eth(amount_of_steth)
        request_id = self._enqueue(int(amount_of_steth), int(amount_of_shares), owner)

        return request_id

    def _check_withdrawal_request_amount(self, amount_of_steth: int):
        if amount_of_steth < self.MIN_STETH_WITHDRAWAL_AMOUNT:
            raise Errors.RequestAmountTooSmall(amount_of_steth)

        if amount_of_steth > self.MAX_STETH_WITHDRAWAL_AMOUNT:
            raise Errors.RequestAmountTooLarge(amount_of_steth)

    def _get_claimable_ether(self, request_id: int, hint: int) -> int:
        if request_id == 0 or request_id > self.get_last_request_id():
            raise Errors.InvalidRequestId(request_id)

        if request_id > self.get_last_finalized_request_id():
            return 0

        request = self.queue[request_id]

        if request.claimed:
            return 0

        return self._calculate_claimable_ether(request, request_id, hint)

    ## ---
    ## pausable library section
    ## ---

    def resume(self):
        self._resume()

    def pause_for(self, duration: Timestamp):
        self._pause_for(duration)

    def pause_until(self, pause_until_inclusive: Timestamp):
        self._pause_until(pause_until_inclusive)
