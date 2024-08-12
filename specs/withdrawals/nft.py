from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional

from specs.lido import Lido
from specs.time_manager import TimeManager
from specs.types.address import Address
from specs.withdrawals.parameters import NFT_NAME, NFT_SYMBOL, WITHDRAWAL_QUEUE_BASE_URI
from specs.withdrawals.queue_base import WithdrawalRequest
from specs.withdrawals.withdrawal_queue import WithdrawalQueue


@dataclass
class WithdrawalQueueERC721(WithdrawalQueue):
    name: str = NFT_NAME
    symbol: str = NFT_SYMBOL
    baseURI: str = WITHDRAWAL_QUEUE_BASE_URI

    time_manager: TimeManager = None
    lido: Lido = None

    token_approvals: Dict[int, str] = field(default_factory=dict)
    operator_approvals: Dict[str, Dict[str, bool]] = field(default_factory=lambda: defaultdict(dict))

    def initialize(
        self,
        time_manager: TimeManager = None,
        lido: Lido = None,
        address: str = Address.ZERO,
    ):
        super().initialize(time_manager, lido, address)

        self.time_manager = time_manager
        self.lido = lido

    def tokenURI(self, request_id: int) -> str:
        if not self._existsAndNotClaimed(request_id):
            raise ValueError("InvalidRequestId")

        return self._constructTokenUri(request_id)

    def finalize(self, last_request_id_to_be_finalized: int, amount_of_ETH: int, max_share_rate: int):
        self._check_resumed()
        self._finalize(last_request_id_to_be_finalized, amount_of_ETH, max_share_rate)

    def balanceOf(self, owner: str) -> int:
        if owner == "0x0":
            raise ValueError("InvalidOwnerAddress")

        return len(self.requests_by_owner.get(owner, set()))

    def ownerOf(self, request_id: int) -> str:
        if request_id == 0 or request_id > self.get_last_request_id():
            raise ValueError("InvalidRequestId")

        request = self.queue.get(request_id)

        if not request or request.claimed:
            raise ValueError("RequestAlreadyClaimed")

        return request.owner

    def approve(self, sender: str, to: str, request_id: int):
        owner = self.ownerOf(request_id)

        if to == owner:
            raise ValueError("ApprovalToOwner")

        if sender != owner and not self.isApprovedForAll(owner, sender):
            raise ValueError("NotOwnerOrApprovedForAll")

        self.token_approvals[request_id] = to

    def getApproved(self, request_id: int) -> Optional[str]:
        if not self._existsAndNotClaimed(request_id):
            raise ValueError("InvalidRequestId")

        return self.token_approvals.get(request_id)

    def setApprovalForAll(self, owner: str, operator: str, approved: bool):
        if operator == owner:
            raise ValueError("ApproveToCaller")

        self.operator_approvals[owner][operator] = approved

    def isApprovedForAll(self, owner: str, operator: str) -> bool:
        return self.operator_approvals.get(owner, {}).get(operator, False)

    def safeTransferFrom(self, sender: str, _from: str, to: str, request_id: int, data: bytes = b""):
        self._transfer(sender, _from, to, request_id)

    def transferFrom(self, sender: str, _from: str, to: str, request_id: int):
        self._transfer(sender, _from, to, request_id)

    def _transfer(self, sender: str, _from: str, to: str, request_id: int):
        if to == Address.ZERO:
            raise ValueError("TransferToZeroAddress")

        if to == _from:
            raise ValueError("TransferToThemselves")

        if request_id == 0 or request_id > self.get_last_request_id():
            raise ValueError("InvalidRequestId")

        request = self.queue.get(request_id)

        if not request or request.claimed:
            raise ValueError("RequestAlreadyClaimed")

        if _from != request.owner:
            raise ValueError("TransferFromIncorrectOwner")

        if not (
            _from == sender or self.isApprovedForAll(_from, sender) or self.token_approvals.get(request_id) == sender
        ):
            raise ValueError("NotOwnerOrApproved")

        self.token_approvals.pop(request_id, None)
        request.owner = to

        self.requests_by_owner[_from].remove(request_id)
        self.requests_by_owner.setdefault(to, []).append(request_id)

    def _existsAndNotClaimed(self, request_id: int) -> bool:
        return (
            request_id > 0
            and request_id <= self.get_last_request_id()
            and not self.queue.get(request_id, WithdrawalRequest()).claimed
        )

    def _constructTokenUri(self, request_id: int) -> str:
        if not self.baseURI:
            return ""

        request = self.queue.get(request_id)
        prev_request = self.queue.get(request_id - 1, WithdrawalRequest())

        uri = f"{self.baseURI}/{request_id}?requested={request.cumulative_stETH - prev_request.cumulative_stETH}&created_at={request.timestamp.value}"

        if request_id <= self.get_last_finalized_request_id():
            uri += f"&finalized={self._get_claimable_ether(request_id, self._find_checkpoint_hint(request_id, 1, self.get_last_checkpoint_index()))}"

        return uri
