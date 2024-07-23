from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from specs.escrow.escrow import Escrow
from specs.lido import Lido
from specs.utils import ether_base

from .config import DualGovernanceConfig
from .errors import Errors


class State(Enum):
    Normal = 1
    VetoSignalling = 2
    VetoSignallingDeactivation = 3
    VetoCooldown = 4
    RageQuit = 5


@dataclass
class DualGovernanceState:
    config: DualGovernanceConfig
    state: State = State.Normal
    entered_at: datetime = field(default_factory=lambda: datetime.min)
    veto_signalling_activation_time: datetime = field(default_factory=lambda: datetime.min)
    signalling_escrow: Escrow = None
    veto_signalling_reactivation_time: datetime = field(default_factory=lambda: datetime.min)
    last_adoptable_state_exited_at: datetime = field(default_factory=lambda: datetime.min)
    rage_quit_escrow: Escrow = None
    rage_quit_round: int = 0
    current_time: datetime = field(default_factory=lambda: datetime.min)

    def initialize(self, escrow_master_copy, stETH_total_supply, current_time, lido: Lido):
        if self.signalling_escrow is not None:
            raise Errors.AlreadyInitialized
        self.current_time = current_time
        self._deploy_new_signalling_escrow(escrow_master_copy, stETH_total_supply, lido)

    def activate_next_state(self):
        old_state = self.state
        if old_state == State.Normal:
            new_state = self._from_normal_state()
        elif old_state == State.VetoSignalling:
            new_state = self._from_veto_signalling_state()
        elif old_state == State.VetoSignallingDeactivation:
            new_state = self._from_veto_signalling_deactivation_state()
        elif old_state == State.VetoCooldown:
            new_state = self._from_veto_cooldown_state()
        elif old_state == State.RageQuit:
            new_state = self._from_rage_quit_state()
        else:
            raise AssertionError

        if old_state != new_state:
            self.state = new_state
            self._handle_state_transition_side_effects(old_state, new_state)

    def check_proposals_creation_allowed(self):
        if not self.is_proposals_creation_allowed():
            raise Errors.ProposalsCreationSuspended

    def check_proposals_adoption_allowed(self):
        if not self.is_proposals_adoption_allowed():
            raise Errors.ProposalsAdoptionSuspended

    def check_can_schedule_proposal(self, proposal_submitted_at):
        if not self.can_schedule_proposal(proposal_submitted_at):
            raise Errors.ProposalsAdoptionSuspended

    def check_tiebreak(self):
        if not self.is_tiebreak():
            raise Errors.NotTie

    def check_reseal_state(self):
        if self.state == State.Normal:
            raise Errors.ResealIsNotAllowedInNormalState

    def current_state(self):
        return self.state

    def can_schedule_proposal(self, proposal_submission_time):
        state = self.state
        if state == State.Normal:
            return True
        if state == State.VetoCooldown:
            return proposal_submission_time <= self.veto_signalling_activation_time
        return False

    def is_proposals_creation_allowed(self):
        state = self.state
        return state != State.VetoSignallingDeactivation and state != State.VetoCooldown

    def is_proposals_adoption_allowed(self):
        state = self.state
        return state == State.Normal or state == State.VetoCooldown

    def is_tiebreak(self):
        if self.is_proposals_adoption_allowed():
            return False

        if self.current_time >= self.config.tie_break_activation_timeout + self.last_adoptable_state_exited_at:
            return True

        if self.state != State.RageQuit:
            return False

        for blocker in self.config.sealable_withdrawal_blockers:  # TODO: implement withdrawal sealable blockers
            if blocker.is_paused():
                return True
        return False

    def get_veto_signalling_state(self):
        is_active = self.state == State.VetoSignalling
        duration = self.get_veto_signalling_duration() if is_active else timedelta(0)
        entered_at = self.entered_at if is_active else datetime.min
        activated_at = self.veto_signalling_activation_time if is_active else datetime.min
        return is_active, duration, entered_at, activated_at

    def get_veto_signalling_duration(self):
        total_support = self.signalling_escrow.get_rage_quit_support()
        return self._calc_dynamic_timelock_duration(total_support)

    def get_veto_signalling_deactivation_state(self):
        is_active = self.state == State.VetoSignallingDeactivation
        duration = self.config.veto_signalling_deactivation_max_duration
        entered_at = self.entered_at if is_active else datetime.min
        return is_active, duration, entered_at

    def _from_normal_state(self):
        return (
            State.VetoSignalling
            if self._is_first_seal_rage_quit_support_crossed(self.signalling_escrow.get_rage_quit_support())
            else State.Normal
        )

    def _from_veto_signalling_state(self):
        rage_quit_support = self.signalling_escrow.get_rage_quit_support()
        if not self._is_dynamic_timelock_duration_passed(rage_quit_support):
            return State.VetoSignalling
        if self._is_second_seal_rage_quit_support_crossed(rage_quit_support):
            return State.RageQuit
        return (
            State.VetoSignallingDeactivation
            if self._is_veto_signalling_reactivation_duration_passed()
            else State.VetoSignalling
        )

    def _from_veto_signalling_deactivation_state(self):
        rage_quit_support = self.signalling_escrow.get_rage_quit_support()
        if not self._is_dynamic_timelock_duration_passed(rage_quit_support):
            return State.VetoSignalling
        if self._is_second_seal_rage_quit_support_crossed(rage_quit_support):
            return State.RageQuit
        if self._is_veto_signalling_deactivation_max_duration_passed():
            return State.VetoCooldown
        return State.VetoSignallingDeactivation

    def _from_veto_cooldown_state(self):
        if not self._is_veto_cooldown_duration_passed():
            return State.VetoCooldown
        return (
            State.VetoSignalling
            if self._is_first_seal_rage_quit_support_crossed(self.signalling_escrow.get_rage_quit_support())
            else State.Normal
        )

    def _from_rage_quit_state(self):
        if not self.rage_quit_escrow.is_rage_quit_finalized():
            return State.RageQuit
        return (
            State.VetoSignalling
            if self._is_first_seal_rage_quit_support_crossed(self.signalling_escrow.get_rage_quit_support())
            else State.VetoCooldown
        )

    def _handle_state_transition_side_effects(self, old_state, new_state):
        timestamp = self.current_time
        self.entered_at = timestamp
        if old_state == State.Normal or old_state == State.VetoCooldown:
            self.last_adoptable_state_exited_at = timestamp

        if new_state == State.Normal and self.rage_quit_round != 0:
            self.rage_quit_round = 0

        if new_state == State.VetoSignalling and old_state != State.VetoSignallingDeactivation:
            self.veto_signalling_activation_time = timestamp

        if old_state == State.VetoSignallingDeactivation and new_state == State.VetoSignalling:
            self.veto_signalling_reactivation_time = timestamp

        if new_state == State.RageQuit:
            signalling_escrow = self.signalling_escrow
            signalling_escrow.start_rage_quit(
                self.config.rage_quit_extension_delay,
                self._calc_rage_quit_withdrawals_timelock(self.rage_quit_round),
            )
            self.rage_quit_escrow = signalling_escrow
            self._deploy_new_signalling_escrow(
                signalling_escrow.MASTER_COPY, signalling_escrow.total_supply, signalling_escrow.lido
            )
            self.rage_quit_round += 1

    def _is_first_seal_rage_quit_support_crossed(self, rage_quit_support):
        return rage_quit_support > self.config.first_seal_rage_quit_support

    def _is_second_seal_rage_quit_support_crossed(self, rage_quit_support):
        return rage_quit_support > self.config.second_seal_rage_quit_support

    def _is_dynamic_timelock_max_duration_passed(self):
        return self.current_time > self.config.dynamic_timelock_max_duration + self.veto_signalling_activation_time

    def _is_dynamic_timelock_duration_passed(self, rage_quit_support):
        dynamic_timelock = self._calc_dynamic_timelock_duration(rage_quit_support)
        return self.current_time > dynamic_timelock + self.veto_signalling_activation_time

    def _is_veto_signalling_reactivation_duration_passed(self):
        return (
            self.current_time > self.config.veto_signalling_min_active_duration + self.veto_signalling_reactivation_time
        )

    def _is_veto_signalling_deactivation_max_duration_passed(self):
        return self.current_time > self.config.veto_signalling_deactivation_max_duration + self.entered_at

    def _is_veto_cooldown_duration_passed(self):
        return self.current_time > self.config.veto_cooldown_duration + self.entered_at

    def _deploy_new_signalling_escrow(self, escrow_master_copy, stETH_total_supply, lido):
        clone = Escrow(escrow_master_copy)
        clone.initialize(escrow_master_copy, stETH_total_supply, lido, self)
        self.signalling_escrow = clone

    def _calc_rage_quit_withdrawals_timelock(self, rage_quit_round):
        if rage_quit_round < self.config.rage_quit_eth_withdrawals_timelock_growth_start_seq_number:
            return self.config.rage_quit_eth_withdrawals_min_timelock
        return self.config.rage_quit_eth_withdrawals_min_timelock + timedelta(
            seconds=(
                self.config.rage_quit_eth_withdrawals_timelock_growth_coeffs[0] * rage_quit_round * rage_quit_round
                + self.config.rage_quit_eth_withdrawals_timelock_growth_coeffs[1] * rage_quit_round
                + self.config.rage_quit_eth_withdrawals_timelock_growth_coeffs[2]
            )
            / ether_base
        )

    def _calc_dynamic_timelock_duration(self, rage_quit_support):
        first_seal_rage_quit_support = self.config.first_seal_rage_quit_support
        second_seal_rage_quit_support = self.config.second_seal_rage_quit_support
        dynamic_timelock_min_duration = self.config.dynamic_timelock_min_duration
        dynamic_timelock_max_duration = self.config.dynamic_timelock_max_duration

        if rage_quit_support < first_seal_rage_quit_support:
            return timedelta(0)

        if rage_quit_support >= second_seal_rage_quit_support:
            return dynamic_timelock_max_duration

        return dynamic_timelock_min_duration + timedelta(
            seconds=(
                (rage_quit_support - first_seal_rage_quit_support)
                * (dynamic_timelock_max_duration - dynamic_timelock_min_duration).total_seconds()
                / (second_seal_rage_quit_support - first_seal_rage_quit_support)
            )
        )

    def shift_current_time(self, delta: timedelta):
        self.current_time = self.current_time + delta
