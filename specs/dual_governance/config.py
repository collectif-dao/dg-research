from dataclasses import dataclass, field
from datetime import timedelta

from parameters import system_parameters
from utils import default, percent_base


@dataclass
class DualGovernanceConfig:
    first_seal_rage_quit_support: int = default(system_parameters["first_seal_rage_quit_support"] * percent_base)
    second_seal_rage_quit_support: int = default(system_parameters["second_seal_rage_quit_support"] * percent_base)

    dynamic_timelock_min_duration: timedelta = default(
        timedelta(days=system_parameters["dynamic_timelock_min_duration"])
    )
    dynamic_timelock_max_duration: timedelta = default(
        timedelta(days=system_parameters["dynamic_timelock_max_duration"])
    )

    veto_signalling_min_active_duration: timedelta = default(
        timedelta(hours=system_parameters["veto_signalling_min_active_duration"])
    )
    veto_signalling_deactivation_max_duration: timedelta = default(
        timedelta(days=system_parameters["veto_signalling_deactivation_max_duration"])
    )
    veto_cooldown_duration: timedelta = default(timedelta(days=system_parameters["veto_cooldown_duration"]))

    rage_quit_extension_delay: timedelta = default(timedelta(days=system_parameters["rage_quit_extension_delay"]))

    rage_quit_eth_withdrawals_min_timelock: timedelta = default(
        timedelta(days=system_parameters["rage_quit_eth_withdrawals_min_timelock"])
    )
    rage_quit_eth_withdrawals_timelock_growth_start_seq_number: int = default(
        system_parameters["rage_quit_eth_withdrawals_timelock_growth_start_seq_number"]
    )

    rage_quit_eth_withdrawals_timelock_growth_coeffs: list = field(
        default_factory=lambda: system_parameters["rage_quit_eth_withdrawals_timelock_growth_coeffs"]
    )

    tie_break_activation_timeout: timedelta = default(timedelta(days=system_parameters["tie_break_activation_timeout"]))
