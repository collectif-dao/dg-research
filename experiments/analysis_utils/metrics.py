from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.special import digamma, polygamma

from model.sys_params import sys_params
from model.types.actors import get_attacker_types


def dirichlet_mle(X: np.ndarray, max_iter: int = 1000, tol: float = 1e-7) -> np.ndarray:
    """
    Maximum likelihood estimation of Dirichlet distribution parameters
    
    Args:
        X: Matrix of proportions where each row sums to 1
        max_iter: Maximum number of iterations for optimization
        tol: Convergence tolerance
        
    Returns:
        Array of estimated concentration parameters (alpha)
    """
    # Initialize alpha with method of moments
    alpha_init = np.mean(X, axis=0) * (np.mean(X, axis=0) * (1 - np.mean(X, axis=0)) / np.var(X, axis=0)).mean()
    alpha = alpha_init

    for _ in range(max_iter):
        alpha_old = alpha.copy()
        
        # Update alpha using Newton's method
        gradient = (digamma(np.sum(alpha)) - digamma(alpha) + 
                   np.mean(np.log(X), axis=0))
        hessian = -polygamma(1, alpha)
        z = polygamma(1, np.sum(alpha))
        c = np.sum(gradient / hessian) / (1/z + np.sum(1/hessian))
        alpha = alpha - (gradient - c) / hessian
        
        # Check convergence
        if np.max(np.abs(alpha - alpha_old)) < tol:
            print(f"Converged after {_} iterations")
            break
            
    return alpha

def get_actor_proportions(start_data_df: pd.DataFrame) -> np.ndarray:
    cols = ["Slow", "Normal", "Quick"]
    n_actors = start_data_df["n_actors"]
    proportions = start_data_df[cols].div(n_actors, axis=0)
    attacker_cols = [actor_type.name for actor_type in get_attacker_types()]
    attacker_num = start_data_df[attacker_cols].sum(axis=1)
    if attacker_num.any():
        proportions["Attackers"] = attacker_num / n_actors
        cols.append("Attackers")
        proportions["Quick"] = proportions["Quick"] - proportions["Attackers"]
    return proportions

def estimate_actor_distribution(start_data_df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """
    Estimate Dirichlet distribution parameters for actor type proportions
    
    Args:
        start_data_df: DataFrame containing start data for different runs
        
    Returns:
        Tuple of (estimated concentration parameters, column names)
    """
    # Get total actors for each run
    n_actors = start_data_df["n_actors"]
    
    # Calculate proportions for each run
    proportions = get_actor_proportions(start_data_df)
    
    # Convert to numpy array for MLE
    X = proportions.values

    print(X)
    
    # Estimate Dirichlet parameters
    alpha = dirichlet_mle(X)
    
    return alpha, proportions.columns.tolist()

def calculate_proposal_stats(proposal_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate proposal statistics per run
    
    Args:
        proposal_df: DataFrame containing proposal data
        
    Returns:
        DataFrame with proposal statistics per run containing:
        - total_proposals: Total number of proposals
        - executed_proposals: Number of executed proposals
        - cancelled_proposals: Number of cancelled proposals
        - scheduled_proposals: Number of scheduled proposals
    """
    stats = (proposal_df
             .groupby('run_id')
             .agg({
                 'proposal_id': 'count',
                 'proposals_status_name': lambda x: {
                     'executed_proposals': (x == 'Executed').sum(),
                     'cancelled_proposals': (x == 'Cancelled').sum(),
                     'scheduled_proposals': (x == 'Scheduled').sum()
                 }
             }))
    
    # Unpack the dictionary from agg
    status_df = pd.DataFrame.from_records(stats['proposals_status_name'].tolist())
    stats = pd.concat([stats['proposal_id'].rename('total_proposals'), status_df], axis=1)
    
    # Add percentage columns
    for col in ['executed', 'cancelled', 'scheduled']:
        stats[f'{col}_percentage'] = (stats[f'{col}_proposals'] / stats['total_proposals'] * 100)
        
    return stats

def calculate_proposal_stats_by_seals(proposal_df: pd.DataFrame, start_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate proposal statistics grouped by seal parameters
    
    Args:
        proposal_df: DataFrame containing proposal data
        start_data_df: DataFrame containing initial parameters including seal values
        
    Returns:
        DataFrame with proposal statistics per seal combination containing:
        - total_proposals: Total number of proposals
        - status percentages for each status
    """
    # Get seal parameters for each run
    seal_params = start_data_df[['run_id', 'first_seal_rage_quit_support', 'second_seal_rage_quit_support', 'attacker_share']].copy()
    
    # Merge proposal data with seal parameters
    merged_df = proposal_df.merge(seal_params, on='run_id')
    
    # Group by seal parameters and calculate statistics
    stats = (merged_df
             .groupby(['first_seal_rage_quit_support', 'second_seal_rage_quit_support', 'attacker_share'])
             .agg({
                 'proposal_id': 'count',
                 'proposals_status_name': lambda x: x.value_counts(normalize=True).to_dict()
             })
             .rename(columns={
                 'proposal_id': 'total_proposals',
                 'proposals_status_name': 'status_percentages'
             }))
    
    # Convert status percentages from dict to separate columns
    status_df = pd.DataFrame(stats['status_percentages'].tolist(), index=stats.index)
    status_df = status_df.fillna(0) * 100  # Convert to percentages
    
    # Combine with total proposals
    result = pd.concat([stats['total_proposals'], status_df], axis=1)
    
    return result

def timesteps_to_hours(timesteps: float) -> float:
    """Convert timesteps to hours using system timedelta_tick"""
    timedelta_tick: timedelta = sys_params['timedelta_tick']
    return timesteps * timedelta_tick.total_seconds() / 3600

def calculate_time_to_first_veto(timestep_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the time to first veto for each run using state transitions
    
    Args:
        timestep_data_df: DataFrame containing timestep data
        
    Returns:
        DataFrame with run_id and times to first veto in both timesteps and hours.
        Values will be NaN for runs with no veto signalling.
    """
    # Find first occurrence of VetoSignalling state (value = 2) for each run
    veto_starts = (timestep_data_df[timestep_data_df['dg_state_value'] == 2]
                  .groupby('run_id')
                  .agg({'timestep': 'min'})
                  .rename(columns={'timestep': 'time_to_first_veto'}))
    
    # Add runs that had no vetoes (with NaN time_to_first_veto)
    all_runs = pd.DataFrame(index=timestep_data_df['run_id'].unique())
    result = all_runs.join(veto_starts)
    result = result.reset_index().rename(columns={'index': 'run_id'})
    
    # Add column with time in hours
    result['time_to_first_veto_hours'] = result['time_to_first_veto'].apply(
        lambda x: timesteps_to_hours(x) if pd.notna(x) else np.nan
    )
    
    return result

def analyze_veto_timing_by_seals(timestep_data_df: pd.DataFrame, start_data_df: pd.DataFrame, additional_columns: tuple[str] = ('attacker_share')) -> pd.DataFrame:
    """
    Analyze how seal parameters affect time to first veto
    
    Args:
        timestep_data_df: DataFrame containing timestep data
        start_data_df: DataFrame containing seal parameters
        
    Returns:
        DataFrame with statistics grouped by seal parameters:
        - veto_rate: Percentage of runs with vetoes
        - mean_time_to_veto: Average time to first veto in timesteps
        - median_time_to_veto: Median time to first veto in timesteps
        - mean_time_to_veto_hours: Average time to first veto in hours
        - median_time_to_veto_hours: Median time to first veto in hours
        - total_runs: Number of runs with this seal combination
    """
    # Get veto timing data
    veto_times = calculate_time_to_first_veto(timestep_data_df)
    
    # Merge with seal parameters
    veto_times_with_params = veto_times.merge(
        start_data_df[['run_id', 'first_seal_rage_quit_support', 'second_seal_rage_quit_support', *additional_columns]], 
        on='run_id'
    )
    
    # Group by seal parameters and calculate statistics
    stats = (veto_times_with_params
             .groupby(['first_seal_rage_quit_support', 'second_seal_rage_quit_support', *additional_columns])
             .agg({
                 'time_to_first_veto': [
                     ('veto_rate', lambda x: x.notna().mean() * 100),
                     ('mean_time_to_veto', 'mean'),
                     ('median_time_to_veto', 'median')
                 ],
                 'time_to_first_veto_hours': [
                     ('mean_time_to_veto_hours', 'mean'),
                     ('median_time_to_veto_hours', 'median')
                 ],
                 'run_id': [('total_runs', 'count')]
             }))
    
    # Flatten column names
    stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
    stats.columns = [col.replace('time_to_first_veto_', '') for col in stats.columns]
    stats.columns = [col.replace('run_id_', '') for col in stats.columns]
    
    return stats

def calculate_pre_first_veto_states(timestep_data_df: pd.DataFrame) -> pd.DataFrame:
    veto_times = calculate_time_to_first_veto(timestep_data_df)
    pre_veto_states = timestep_data_df.merge(veto_times[['run_id', 'time_to_first_veto']], on='run_id', how='left')
    pre_veto_states = pre_veto_states[pre_veto_states['timestep'] == pre_veto_states['time_to_first_veto'] - 1]
    return pre_veto_states

def calculate_pre_first_veto_stats(timestep_data_df: pd.DataFrame, start_data_df: pd.DataFrame) -> pd.DataFrame:
    pre_veto_states = calculate_pre_first_veto_states(timestep_data_df)
    
    # Merge with both seal parameters
    pre_veto_states = pre_veto_states.merge(
        start_data_df[['run_id', 'first_seal_rage_quit_support', 'second_seal_rage_quit_support', 'attacker_share']], 
        on='run_id', 
        how='left'
    )
    
    # Calculate statistics for each actor type grouped by seal parameters
    stats = (pre_veto_states
             .groupby(['first_seal_rage_quit_support', 'second_seal_rage_quit_support', 'attacker_share'])
             .agg({
                 'actors_locked_Slow': ['mean', 'median', 'std'],
                 'actors_locked_Normal': ['mean', 'median', 'std'],
                 'actors_locked_Quick': ['mean', 'median', 'std']
             }))
    
    # Flatten column names
    stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
    
    return stats

def calculate_state_counts(timestep_data_df: pd.DataFrame) -> pd.DataFrame:
    # Get counts per state
    state_counts = timestep_data_df.groupby(['run_id', 'dg_state_name']).size().unstack(fill_value=0)
    
    # Convert timesteps to hours using existing function
    state_counts_hours = state_counts.apply(timesteps_to_hours)
    
    # Combine both counts into single dataframe
    state_counts_df = pd.concat([
        state_counts.add_suffix('_timesteps'),
        state_counts_hours.add_suffix('_hours')
    ], axis=1)
    
    return state_counts_df
    
