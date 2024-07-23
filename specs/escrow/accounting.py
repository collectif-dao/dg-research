from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List

from specs.types.eth_value import ETHValue
from specs.types.index_one import IndexOneBased
from specs.types.shares_value import SharesValue
from specs.types.timestamp import Timestamp

from .errors import Errors


class WithdrawalRequestStatus:
    amount_of_stETH: int
    amount_of_shares: int
    owner: str
    timestamp: int
    is_finalized: bool = False
    is_claimed: bool = False

    def __init__(self, amount_of_stETH, amount_of_shares, owner, timestamp, is_finalized, is_claimed):
        self.amount_of_stETH = amount_of_stETH
        self.amount_of_shares = amount_of_shares
        self.owner = owner
        self.timestamp = timestamp
        # self.is_finalized = is_finalized
        # self.is_claimed = is_claimed


class UnstETHRecordStatus(Enum):
    NotLocked = 0
    Locked = 1
    Finalized = 2
    Claimed = 3
    Withdrawn = 4


@dataclass
class HolderAssets:
    stETHLockedShares: SharesValue = field(default_factory=lambda: SharesValue(0))
    unstETHLockedShares: SharesValue = field(default_factory=lambda: SharesValue(0))
    lastAssetsLockTimestamp: Timestamp = field(default_factory=lambda: Timestamp(0))
    unstETHIds: List[int] = field(default_factory=list)


@dataclass
class UnstETHAccounting:
    unfinalizedShares: SharesValue = field(default_factory=lambda: SharesValue(0))
    finalizedETH: ETHValue = field(default_factory=lambda: ETHValue(0))


@dataclass
class StETHAccounting:
    lockedShares: SharesValue = field(default_factory=lambda: SharesValue(0))
    claimedETH: ETHValue = field(default_factory=lambda: ETHValue(0))


@dataclass
class UnstETHRecord:
    index: IndexOneBased = field(default_factory=lambda: IndexOneBased(0))
    lockedBy: str = field(default_factory=lambda: "")
    status: UnstETHRecordStatus = field(default_factory=lambda: UnstETHRecordStatus.NotLocked)
    shares: SharesValue = field(default_factory=lambda: SharesValue(0))
    claimableAmount: ETHValue = field(default_factory=lambda: ETHValue(0))


@dataclass
class AssetsAccountingState:
    stETHTotals: StETHAccounting = field(default_factory=lambda: StETHAccounting())
    unstETHTotals: UnstETHAccounting = field(default_factory=lambda: UnstETHAccounting())
    assets: Dict[str, HolderAssets] = field(default_factory=dict)
    unstETHRecords: Dict[int, UnstETHRecord] = field(default_factory=dict)


@dataclass(frozen=True)
class AssetsAccounting:
    state: AssetsAccountingState = field(default_factory=lambda: AssetsAccountingState())

    def accountStETHSharesLock(self, holder: str, shares: SharesValue):
        """
        Account for locked stETH shares by a holder.

        Args:
            holder (str): The address of the holder.
            shares (int): The number of shares to lock.
        """

        self._checkNonZeroShares(shares)

        self.state.stETHTotals.lockedShares += shares

        if holder not in self.state.assets:
            self.state.assets[holder] = HolderAssets()

        self.state.assets[holder].stETHLockedShares += shares
        self.state.assets[holder].lastAssetsLockTimestamp = Timestamp(int(datetime.now().timestamp()))

    def accountStETHSharesUnlock(self, holder: str) -> SharesValue:
        shares = self.state.assets[holder].stETHLockedShares
        self.accountStETHSharesUnlock(self, holder, shares)

        return shares

    def accountStETHSharesUnlock(self, holder: str, shares: SharesValue):
        self._checkNonZeroShares(shares)

        if self.state.assets[holder].stETHLockedShares < shares:
            raise Errors.InvalidSharesValue

        self.state.stETHTotals.lockedShares -= shares
        self.state.assets[holder].stETHLockedShares -= shares

    def accountStETHSharesWithdraw(self, holder: str) -> ETHValue:
        assets = self.state.assets[holder]
        stETHSharesToWithdraw = assets.stETHLockedShares

        self._checkNonZeroShares(stETHSharesToWithdraw)

        assets.stETHLockedShares = SharesValue(0)

        ethWithdrawn = SharesValue.calc_eth_value(
            self.state.stETHTotals.claimedETH, stETHSharesToWithdraw, self.state.stETHTotals.lockedShares
        )

        return ethWithdrawn

    def accountClaimedStETH(self, amount: ETHValue):
        self.state.stETHTotals.claimedETH += amount

    ## ---
    ## unstETH operations
    ## ---

    def accountUnstETHLock(self, holder: str, unstETHIds: List[int], statuses: List[WithdrawalRequestStatus]):
        if len(unstETHIds) != len(statuses):
            raise Errors.IncorrectParameters

        totalUnstETHLocked = SharesValue(0)
        for i in range(len(unstETHIds)):
            totalUnstETHLocked += self._addUnstETHRecord(holder, unstETHIds[i], statuses[i])

        if holder not in self.state.assets:
            self.state.assets[holder] = HolderAssets()

        self.state.assets[holder].lastAssetsLockTimestamp = Timestamp(int(datetime.now().timestamp()))
        self.state.assets[holder].unstETHLockedShares += totalUnstETHLocked
        self.state.unstETHTotals.unfinalizedShares += totalUnstETHLocked

    def accountUnstETHUnlock(self, holder: str, unstETHIds: List[int]):
        totalSharesUnlocked = SharesValue(0)
        totalFinalizedSharesUnlocked = SharesValue(0)
        totalFinalizedAmountUnlocked = ETHValue(0)

        for unstETHId in unstETHIds:
            values: tuple[SharesValue, ETHValue] = self._removeUnstETHRecord(holder, unstETHId)
            sharesUnlocked = values[0]
            finalizedAmountUnlocked = values[1]

            totalSharesUnlocked = totalSharesUnlocked + sharesUnlocked

            if finalizedAmountUnlocked > ETHValue(0):
                totalFinalizedAmountUnlocked = totalFinalizedAmountUnlocked + finalizedAmountUnlocked
                totalFinalizedSharesUnlocked = totalFinalizedSharesUnlocked + sharesUnlocked

        self.state.assets[holder].unstETHLockedShares -= totalSharesUnlocked
        self.state.unstETHTotals.finalizedETH -= totalFinalizedAmountUnlocked
        self.state.unstETHTotals.unfinalizedShares -= totalSharesUnlocked - totalFinalizedSharesUnlocked

    def accountUnstETHFinalized(self, unstETHIds: List[int], claimableAmounts: List[int]):
        if len(unstETHIds) != len(claimableAmounts):
            raise Errors.IncorrectParameters

        totalAmountFinalized = ETHValue(0)
        totalSharesFinalized = SharesValue(0)

        for i in range(len(unstETHIds)):
            values: tuple[SharesValue, ETHValue] = self._finalizeUnstETHRecord(unstETHIds[i], claimableAmounts[i])
            sharesFinalized = values[0]
            amountFinalized = values[1]

            totalSharesFinalized = totalSharesFinalized + sharesFinalized
            totalAmountFinalized = totalAmountFinalized + amountFinalized

        self.state.unstETHTotals.finalizedETH += totalAmountFinalized
        self.state.unstETHTotals.unfinalizedShares -= totalSharesFinalized

    def accountUnstETHClaimed(self, unstETHIds: List[int], claimableAmounts: List[int]) -> ETHValue:
        if len(unstETHIds) != len(claimableAmounts):
            raise Errors.IncorrectParameters

        totalAmountClaimed = ETHValue(0)

        for i in range(len(unstETHIds)):
            claimableAmount = ETHValue.from_uint256(claimableAmounts[i])
            totalAmountClaimed += claimableAmount
            self._claimUnstETHRecord(unstETHIds[i], claimableAmount)

        return totalAmountClaimed

    def accountUnstETHWithdraw(self, holder: str, unstETHIds: List[int]) -> ETHValue:
        amountWithdrawn = ETHValue(0)
        for unstETHId in unstETHIds:
            amountWithdrawn += self._withdrawUnstETHRecord(holder, unstETHId)

        return amountWithdrawn

    ## ---
    ## Getter functions
    ## ---

    def getLockedAssetsTotals(self) -> tuple[SharesValue, ETHValue]:
        finalizedETH = self.state.unstETHTotals.finalizedETH
        unfinalizedShares = self.state.stETHTotals.lockedShares + self.state.unstETHTotals.unfinalizedShares

        return unfinalizedShares, finalizedETH

    def checkAssetsUnlockDelayPassed(self, holder: str, assetsUnlockDelay: int):
        assetsUnlockAllowedAfter = Timestamp(
            self.state.assets[holder].lastAssetsLockTimestamp.value + assetsUnlockDelay
        )

        if Timestamp.now() <= assetsUnlockAllowedAfter:
            raise Errors.AssetsUnlockDelayNotPassed

    ## ---
    ## Internal methods
    ## ---

    def _checkNonZeroShares(self, shares: SharesValue):
        if shares.value == 0:
            raise Errors.InvalidSharesValue

    def _addUnstETHRecord(self, holder: str, unstETHId: int, status: WithdrawalRequestStatus) -> SharesValue:
        if status.is_finalized:
            raise Errors.InvalidUnstETHStatus

        assert status.is_claimed is not True

        if unstETHId not in self.state.unstETHRecords:
            self.state.unstETHRecords[unstETHId] = UnstETHRecord()

        if self.state.unstETHRecords[unstETHId].status != UnstETHRecordStatus.NotLocked:
            raise Errors.InvalidUnstETHStatus

        if holder not in self.state.assets:
            self.state.assets[holder] = HolderAssets()

        assets: HolderAssets = self.state.assets[holder]
        assets.unstETHIds.append(unstETHId)

        shares = SharesValue(status.amount_of_shares)
        self.state.unstETHRecords[unstETHId] = UnstETHRecord(
            index=IndexOneBased.fromValue(len(assets.unstETHIds)),
            lockedBy=holder,
            status=UnstETHRecordStatus.Locked,
            shares=shares,
            claimableAmount=ETHValue(0),
        )

        return shares

    def _removeUnstETHRecord(self, holder: str, unstETHId: int) -> tuple[SharesValue, ETHValue]:
        unstETHRecord: UnstETHRecord = self.state.unstETHRecords[unstETHId]

        if unstETHRecord.lockedBy != holder:
            raise Errors.InvalidUnstETHHolder

        if unstETHRecord.status == UnstETHRecordStatus.NotLocked:
            raise Errors.InvalidUnstETHStatus

        sharesUnlocked = unstETHRecord.shares
        finalizedAmountUnlocked: ETHValue = ETHValue(0)

        if unstETHRecord.status == UnstETHRecordStatus.Finalized:
            finalizedAmountUnlocked = unstETHRecord.claimableAmount

        assets: HolderAssets = self.state.assets[holder]
        unstETHIdIndex: IndexOneBased = unstETHRecord.index
        lastUnstETHIdIndex: IndexOneBased = IndexOneBased.fromValue(len(assets.unstETHIds))

        if lastUnstETHIdIndex != unstETHIdIndex:
            lastUnstETHId = assets.unstETHIds[lastUnstETHIdIndex.get_value()]
            assets.unstETHIds[unstETHIdIndex.get_value()] = lastUnstETHId
            self.state.unstETHRecords[lastUnstETHId].index = unstETHIdIndex

        assets.unstETHIds.pop()
        del self.state.unstETHRecords[unstETHId]

        return sharesUnlocked, finalizedAmountUnlocked

    def _finalizeUnstETHRecord(self, unstETHId: int, claimableAmount: int) -> tuple[SharesValue, ETHValue]:
        unstETHRecord: UnstETHRecord = self.state.unstETHRecords[unstETHId]

        if claimableAmount == 0 or unstETHRecord.status != UnstETHRecordStatus.Locked:
            return SharesValue(0), ETHValue(0)

        sharesFinalized = unstETHRecord.shares
        amountFinalized = ETHValue.from_uint256(claimableAmount)

        unstETHRecord.status = UnstETHRecordStatus.Finalized
        unstETHRecord.claimableAmount = amountFinalized

        self.state.unstETHRecords[unstETHId] = unstETHRecord

        return sharesFinalized, amountFinalized

    def _claimUnstETHRecord(self, unstETHId: int, claimableAmount: ETHValue):
        unstETHRecord: UnstETHRecord = self.state.unstETHRecords[unstETHId]

        if (unstETHRecord.status != UnstETHRecordStatus.Locked) & (
            unstETHRecord.status != UnstETHRecordStatus.Finalized
        ):
            raise Errors.InvalidUnstETHStatus

        if unstETHRecord.status == UnstETHRecordStatus.Finalized:
            if unstETHRecord.claimableAmount != claimableAmount:
                raise Errors.InvalidClaimableAmount
        else:
            unstETHRecord.claimableAmount = claimableAmount

        unstETHRecord.status = UnstETHRecordStatus.Claimed

        self.state.unstETHRecords[unstETHId] = unstETHRecord

    def _withdrawUnstETHRecord(self, holder: str, unstETHId: int) -> ETHValue:
        unstETHRecord: UnstETHRecord = self.state.unstETHRecords[unstETHId]

        if unstETHRecord.status != UnstETHRecordStatus.Claimed:
            raise Errors.InvalidUnstETHStatus

        if unstETHRecord.lockedBy != holder:
            raise Errors.InvalidUnstETHHolder

        unstETHRecord.status = UnstETHRecordStatus.Withdrawn
        amountWithdrawn = unstETHRecord.claimableAmount

        return amountWithdrawn
