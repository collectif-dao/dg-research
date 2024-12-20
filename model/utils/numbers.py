from specs.utils import ether_base


def calculate_required_deposit(total_supply: int, target_percentage: int) -> int:
    """
    Calculate required deposit to achieve target_percentage of the final total supply.
    Using the formula: required_deposit = (current_supply * target_percentage) / (100 - target_percentage)
    """
    return (total_supply * target_percentage) // (100 - target_percentage)


def calculate_time_to_prepare_dilution(total_supply: int, target_percentage: int, deposit_cap: int):
    required_deposit = calculate_required_deposit(total_supply, target_percentage)
    days_to_prepare = (required_deposit + deposit_cap - 1) // deposit_cap
    return days_to_prepare


def calculate_time_to_prepare_funds_deposit(deposit_amount: int, deposit_cap: int = 300_000 * ether_base):
    days_to_prepare = (deposit_amount + deposit_cap - 1) // deposit_cap
    return days_to_prepare


def calculate_time_for_withdrawal(amount_of_steth: int, lido_exit_share: int, churn_rate: int):
    lido_withdrawal_limit = max_withdrawal_per_day(churn_rate, lido_exit_share)

    if amount_of_steth > lido_withdrawal_limit:
        return (amount_of_steth // lido_withdrawal_limit) + 1

    return 1


def max_withdrawal_per_day(churn_rate: int, lido_exit_share: int):
    daily_withdrawal_limit = churn_rate * 32 * 225
    return int(daily_withdrawal_limit * lido_exit_share) * 10**18
