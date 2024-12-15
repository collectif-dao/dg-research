import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import cm

from experiments.analysis_utils.metrics import (
    calculate_pre_first_veto_states, calculate_state_counts,
    calculate_time_to_first_veto)
from model.types.actors import get_attacker_types


def add_proposal_data_to_timeplot(ax: plt.Axes,
                                  proposal_df: pd.DataFrame,
                                  lines: tuple[int, int, int, int, int] = (1, 1, 1, 1, 1),
                                  proposal_legend=True
                                  ) -> None:
    line_types = [
        ((0, (1, 20)), "submission"),
        ((0, (1, 10)), "earliest possible execution"),
        ("dotted", "schedule"),
        ((0, (5, 10)), "possible execution time"),
        ("-", "actual execution"),
    ]

    ylim = ax.get_ylim()
    colors = cm.rainbow(np.linspace(0, 1, len(proposal_df)))

    used_line_types = []

    for i, proposal_id in enumerate(proposal_df.index):
        proposal = proposal_df.loc[proposal_id]

        submission_timestep = proposal.submittedAt
        if lines[0]:
            submission_time_line = ax.plot(
                np.repeat(submission_timestep, 2), [0, ylim[1]], linestyle=line_types[0][0], c=colors[i]
            )
            used_line_types.append(0)

        earliest_execution_timestep = submission_timestep + 5 * 24 / 3

        if lines[1]:
            early_execution_time_line = ax.plot(
                np.repeat(earliest_execution_timestep, 2), [0, ylim[1]], linestyle=line_types[1][0], c=colors[i]
            )
            used_line_types.append(1)

        schedule_timestep = proposal.scheduledAt
        if schedule_timestep > submission_timestep:
            if lines[2]:
                schedule_time_line = ax.plot(
                    np.repeat(schedule_timestep, 2), [0, ylim[1]], linestyle=line_types[2][0], c=colors[i]
                )
                used_line_types.append(2)
            possible_execution_timestep = schedule_timestep + 3 * 24 / 3
            if lines[3]:
                possible_execution_time_line = ax.plot(
                    np.repeat(possible_execution_timestep, 2), [0, ylim[1]], linestyle=line_types[3][0], c=colors[i]
                )
                used_line_types.append(3)

        execution_timestep = proposal.executedAt
        if execution_timestep > schedule_timestep:
            if lines[4]:
                real_execution_time_line = ax.plot(
                    np.repeat(execution_timestep, 2), [0, ylim[1]], linestyle=line_types[4][0], c=colors[i]
                )
                used_line_types.append(4)
        ax.set_ylim(ylim)
    if proposal_legend:
        for i, color in enumerate(colors):
            ax.plot([], [], c=color, label=f"Proposal {proposal_df.proposal_id.iloc[i]}")
    for i in used_line_types:
        linestyle, label = line_types[i]
        ax.plot([], [], linestyle=linestyle, c="gray", label=label)


def plot_reaction_speed_distribution(
    start_data_df: pd.DataFrame,
    run_id: int,
    ax: plt.Axes | None = None,
    title: str = "Actors reaction speed"
) -> plt.Axes:
    """
    Plot pie chart of actor reaction speed distribution for a single run
    
    Args:
        start_data_df: DataFrame containing start data for different runs
        run_id: ID of the run to plot
        ax: Optional matplotlib axes to plot on
        title: Plot title
        
    Returns:
        matplotlib axes with the plot
    """
    if ax is None:
        _, ax = plt.subplots()
    
    # Get data for specific run
    run_data = start_data_df[start_data_df["run_id"] == run_id].copy()
    
    # Calculate attackers total
    run_data["Attackers"] = run_data[[actor_type.name for actor_type in get_attacker_types()]].sum(axis=1)

    # Prepare data for plotting
    cols = ["Slow", "Normal", "Quick", "Attackers"]
    values = np.array(run_data[cols])[0]
    # Subtract attackers from Quick actors as they're included there
    values[2] = values[2] - values[3]

    # Remove attackers if there are none
    if values[3] == 0:
        cols.pop()
        values = values[:-1]

    n_actors = run_data["n_actors"].iloc[0]

    # Format function for labels
    def fmt(x: float) -> str:
        return f"{int(x.round())}% ({int((x * n_actors / 100).round())})"

    ax.pie(values, labels=cols, autopct=fmt)
    ax.set_title(title)
    
    return ax

def plot_token_distribution(
    timestep_data_df: pd.DataFrame,
    run_id: int,
    ax: plt.Axes | None = None,
    title: str = "Tokens by reaction speed"
) -> plt.Axes:
    """
    Plot pie chart of token distribution across actor reaction speeds for a single run
    
    Args:
        timestep_data_df: DataFrame containing timestep data for different runs
        run_id: ID of the run to plot
        ax: Optional matplotlib axes to plot on
        title: Plot title
        
    Returns:
        matplotlib axes with the plot
    """
    if ax is None:
        _, ax = plt.subplots()
    
    # Get data for specific run at timestep 1
    timestep_data_df_run = timestep_data_df[timestep_data_df["run_id"] == run_id]
    timestep_data_df_run_start = timestep_data_df_run[timestep_data_df_run["timestep"] == 1].copy()
    
    # Calculate attackers total
    attacker_labels = [actor_type.name for actor_type in get_attacker_types()]
    timestep_data_df_run_start["balance_Attackers"] = sum(
        timestep_data_df_run_start[f"balance_{label}"] for label in attacker_labels
    )

    # Prepare data for plotting
    cols = ["Slow", "Normal", "Quick", "Attackers"]
    values = np.array(timestep_data_df_run_start[[f"balance_{col}" for col in cols]])[0]
    values[2] = values[2] - values[3]
    
    # Remove attackers if there are none
    if values[3] == 0:
        cols.pop()
        values = values[:-1]

    initial_tokens = timestep_data_df_run_start["actors_total_balance"].iloc[0]
    
    # Format function for labels
    def fmt(x: float) -> str:
        return f"{int(x.round())}% ({x * initial_tokens / 100:.2f})"

    ax.pie(values, labels=cols, autopct=fmt)
    ax.set_title(title)
    
    return ax

def plot_pre_veto_locked_by_reaction_time_distributions(timestep_data_df: pd.DataFrame, start_data_df: pd.DataFrame, plot_token_distribution: bool = False) -> None:
    """
    Create boxplots showing the distribution of locked actors or tokens by type and first seal support
    
    Args:
        timestep_data_df: DataFrame containing timestep data
        start_data_df: DataFrame containing seal parameters
        tokens: Boolean flag to determine whether to plot token distribution instead of actor distribution
    """
    import matplotlib.pyplot as plt
    import seaborn as sns

    # Get pre-veto states and merge with seal parameters
    pre_veto_states = calculate_pre_first_veto_states(timestep_data_df)
    pre_veto_states = pre_veto_states.merge(
        start_data_df[['run_id', 'first_seal_rage_quit_support', 'second_seal_rage_quit_support']], 
        on='run_id', 
        how='left'
    )
    
    # Determine the value_vars based on the tokens flag
    if plot_token_distribution:
        value_vars = ['locked_Slow', 'locked_Normal', 'locked_Quick']
        value_name = 'locked_tokens'
        var_name = 'token_type'
        ylabel = 'Number of Locked Tokens'
        title = 'Distribution of Locked Tokens by Type and First Seal Support'
    else:
        value_vars = ['actors_locked_Slow', 'actors_locked_Normal', 'actors_locked_Quick']
        value_name = 'locked_actors'
        var_name = 'actor_type'
        ylabel = 'Number of Locked Actors'
        title = 'Distribution of Locked Actors by Type and First Seal Support'
    
    # Reshape data for plotting
    plot_data = pd.melt(
        pre_veto_states,
        id_vars=['first_seal_rage_quit_support'],
        value_vars=value_vars,
        var_name=var_name,
        value_name=value_name
    )
    
    # Clean up labels by removing prefix
    plot_data[var_name] = plot_data[var_name].str.replace('actors_locked_', '').str.replace('locked_', '')
    
    # Store original parameters
    original_params = {
        'font.size': plt.rcParams['font.size'],
        'lines.linewidth': plt.rcParams['lines.linewidth']
    }

    # Set temporary parameters
    plt.rcParams.update({'font.size': 14, 'lines.linewidth': 2})

    try:
        # Create the plot
        plt.figure(figsize=(10, 6))
        sns.boxplot(
            data=plot_data,
            x='first_seal_rage_quit_support',
            y=value_name,
            hue=var_name,
            palette='Set2'
        )
        
        # Convert x-axis labels to percentages
        current_ticks = plt.gca().get_xticks()
        current_labels = plt.gca().get_xticklabels()
        plt.gca().set_xticklabels([f'{float(label.get_text())*100:.2f}%' for label in current_labels])
        
        plt.title(title)
        plt.xlabel('First Seal Rage Quit Support (%)')
        plt.ylabel(ylabel)
        plt.legend(title=var_name.replace('_', ' ').title())
        plt.xticks(rotation=0)
        
        plt.tight_layout()
    finally:
        # Restore original parameters
        plt.rcParams.update(original_params)

def plot_state_distribution(timestep_data_df: pd.DataFrame, in_timesteps: bool = True, collapse_non_normal: bool = False) -> None:
    """
    Plot the distribution of time spent in each state, converted to hours.

    Args:
        state_counts: DataFrame with counts of timesteps in each state per run.
        timestep_to_hour: Conversion factor from timesteps to hours.
        collapse_non_normal: Boolean flag to collapse all non-Normal states into one box.
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    state_counts = calculate_state_counts(timestep_data_df)

    # Select columns based on suffix
    cols = []
    for col in state_counts.columns:
        if in_timesteps and '_timesteps' in col:
            cols.append(col)
        elif not in_timesteps and '_hours' in col:
            cols.append(col)
    
    plot_data = state_counts[cols]
    plot_data.columns = [col.replace('_timesteps', '').replace('_hours', '') for col in cols]

    if collapse_non_normal:
        # Collapse all non-'Normal' states into one
        plot_data['Other'] = plot_data.drop(columns=['Normal'], errors='ignore').sum(axis=1)
        plot_data = plot_data[['Normal', 'Other']]

    # Store original parameters
    original_params = {
        'font.size': plt.rcParams['font.size'],
        'lines.linewidth': plt.rcParams['lines.linewidth']
    }

    # Set temporary parameters
    plt.rcParams.update({'font.size': 14, 'lines.linewidth': 2})

    try:
        plt.figure(figsize=(10, 4))
        sns.boxplot(data=plot_data)
        plt.xticks(rotation=0)
        plt.title(f'Distribution of Time Spent in Each State ({"Timesteps" if in_timesteps else "Hours"})')
        plt.ylabel(f'Time Spent ({"Timesteps" if in_timesteps else "Hours"})')
        plt.tight_layout()
        plt.show()
    finally:
        # Restore original parameters
        plt.rcParams.update(original_params)

def plot_attack_success_rate(timestep_data_df_full, start_data_df_full):
    """
    Plot attack success rate vs attacker share with confidence intervals
    using individual run data.
    """
    from experiments.analysis_utils.metrics import calculate_time_to_first_veto

    sns.set_context('talk')

    # Calculate veto times for each run
    veto_times = calculate_time_to_first_veto(timestep_data_df_full)
    
    # Merge with start data to get attacker share
    analysis_df = veto_times.merge(
        start_data_df_full[['run_id', 'attacker_share']], 
        on='run_id'
    )
    
    # Mark runs as successful (no veto) or failed (veto occurred)
    analysis_df['attack_succeeded'] = analysis_df['time_to_first_veto'].isna()
    analysis_df['attack_success_binary'] = analysis_df['attack_succeeded'].astype(int) * 100
    
    # Create the plot
    ratio = 6 / 10
    base_size = 8
    plt.figure(figsize=(base_size, base_size * ratio))
    sns.lineplot(
        data=analysis_df,
        x='attacker_share',
        y='attack_success_binary',
        errorbar=('ci', 95),  # 95% confidence interval
        marker='o'
    )
    
    plt.title('Attack Success Rate vs Attacker Share')
    plt.xlabel('Attacker Share')
    plt.ylabel('Attack Success Rate')
    
    # Format x-axis as percentage
    current_values = plt.gca().get_xticks()
    plt.gca().set_xticklabels([f'{x:.0%}' for x in current_values])
    current_values = plt.gca().get_yticks()
    plt.gca().set_yticklabels([f'{x:.0f}%' for x in current_values])
    
    plt.grid(True)
    plt.show()

def plot_veto_success_rate_by_column(timestep_data_df_full, start_data_df_full, column: str, xlabel:str = None):
    """
    Plot attack success rate vs attacker share with confidence intervals
    using individual run data.
    """
    from experiments.analysis_utils.metrics import calculate_time_to_first_veto

    sns.set_context('talk')

    # Calculate veto times for each run
    veto_times = calculate_time_to_first_veto(timestep_data_df_full)
    
    # Merge with start data to get attacker share
    analysis_df = veto_times.merge(
        start_data_df_full[['run_id', column]], 
        on='run_id'
    )
    
    # Mark runs as successful (no veto) or failed (veto occurred)
    analysis_df['veto_succeeded'] = analysis_df['time_to_first_veto'].notna()
    analysis_df['veto_success_binary'] = analysis_df['veto_succeeded'].astype(int) * 100
    
    # Create the plot
    ratio = 6 / 10
    base_size = 8
    plt.figure(figsize=(base_size, base_size * ratio))
    sns.lineplot(
        data=analysis_df,
        x=column,
        y='veto_success_binary',
        errorbar=('ci', 95)  # 95% confidence interval
    )
    
    # plt.title(f'Veto Success Rate vs {column}')
    if xlabel is None:
        xlabel = f'{column}'
    plt.xlabel(f'{xlabel}')
    plt.ylabel('Veto Success Rate')
    
    # Format x-axis as percentage
    current_values = plt.gca().get_xticks()
    plt.gca().set_xticklabels([f'{x:.0f}%' for x in current_values])
    current_values = plt.gca().get_yticks()
    plt.gca().set_yticklabels([f'{x:.0f}%' for x in current_values])
    
    plt.grid(True)
    plt.show()

def plot_expected_attacker_gains(timestep_data_df_full, start_data_df_full):
    """
    Plot expected relative gains for attackers vs attacker share with confidence intervals.
    Relative gains show how much attackers can multiply their initial share.
    """
    from experiments.analysis_utils.metrics import calculate_time_to_first_veto

    # Calculate veto times for each run
    veto_times = calculate_time_to_first_veto(timestep_data_df_full)
    
    # Merge with start data to get attacker share
    analysis_df = veto_times.merge(
        start_data_df_full[['run_id', 'attacker_share']], 
        on='run_id'
    )
    
    # Mark runs as successful (no veto) or failed (veto occurred)
    analysis_df['attack_succeeded'] = analysis_df['time_to_first_veto'].isna()
    
    # Calculate relative gains
    # If attack succeeds: (initial_share + (1-initial_share)) / initial_share = 1/initial_share
    # If attack fails: initial_share/initial_share = 1
    analysis_df['relative_gains'] = np.where(
        analysis_df['attack_succeeded'],
        1/analysis_df['attacker_share'],  # Success: gain everything
        1  # Failure: keep original share
    )
    
    # Create the plot
    ratio = 6 / 10
    base_size = 8
    plt.figure(figsize=(base_size, base_size * ratio))
    sns.lineplot(
        data=analysis_df,
        x='attacker_share',
        y='relative_gains',
        errorbar=('ci', 95),  # 95% confidence interval
        marker='o'
    )
    
    plt.title('Expected Relative Gains vs Attacker Share')
    plt.xlabel('Attacker Share')
    plt.ylabel('Expected Relative Gains (multiplier)')
    
    # Format x-axis as percentage
    current_values = plt.gca().get_xticks()
    plt.gca().set_xticklabels([f'{x:.0%}' for x in current_values])
    
    plt.grid(True)
    plt.show()