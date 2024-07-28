from dataclasses import dataclass, field
from datetime import timedelta

from specs.parameters import system_parameters
from specs.types.timestamp import Timestamp
from specs.utils import default, percent_base


@dataclass
class DualGovernanceConfig:
    first_seal_rage_quit_support: int = default(system_parameters["first_seal_rage_quit_support"] * percent_base)
    second_seal_rage_quit_support: int = default(system_parameters["second_seal_rage_quit_support"] * percent_base)

    dynamic_timelock_min_duration: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["dynamic_timelock_min_duration"]).total_seconds()))
    )
    dynamic_timelock_max_duration: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["dynamic_timelock_max_duration"]).total_seconds()))
    )

    veto_signalling_min_active_duration: Timestamp = default(
        Timestamp(int(timedelta(hours=system_parameters["veto_signalling_min_active_duration"]).total_seconds()))
    )
    veto_signalling_deactivation_max_duration: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["veto_signalling_deactivation_max_duration"]).total_seconds()))
    )
    veto_cooldown_duration: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["veto_cooldown_duration"]).total_seconds()))
    )

    rage_quit_extension_delay: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["rage_quit_extension_delay"]).total_seconds()))
    )

    rage_quit_eth_withdrawals_min_timelock: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["rage_quit_eth_withdrawals_min_timelock"]).total_seconds()))
    )
    rage_quit_eth_withdrawals_timelock_growth_start_seq_number: int = default(
        system_parameters["rage_quit_eth_withdrawals_timelock_growth_start_seq_number"]
    )

    rage_quit_eth_withdrawals_timelock_growth_coeffs: list = field(
        default_factory=lambda: system_parameters["rage_quit_eth_withdrawals_timelock_growth_coeffs"]
    )

    tie_break_activation_timeout: Timestamp = default(
        Timestamp(int(timedelta(days=system_parameters["tie_break_activation_timeout"]).total_seconds()))
    )
