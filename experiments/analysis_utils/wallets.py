import numpy as np
import pandas as pd
from numba import boolean, float64, int64, jit


def add_total_token_share(wallet_df):
    wallet_df['total_token_share'] = wallet_df['total'] / wallet_df['total'].sum() * 100
    return wallet_df

def get_token_array(wallet_df, wallet_types):
    return np.array(
        wallet_df[wallet_df.type.isin(wallet_types)]['total_token_share'].sort_values(
            ascending=False))

@jit(nopython=True)
def recursive_count(token_array, min_remaining_sums, threshold, start_idx, remaining_depth, current_sum, valid_combinations):
    n = len(token_array)
    
    # Early termination with more aggressive pruning
    remaining_needed = threshold - current_sum
    if remaining_depth * token_array[start_idx] < remaining_needed:
        return 0, -1
        
    if remaining_depth == 1:
        # Vectorized base case
        count = 0
        end_idx = n
        for i in range(start_idx, end_idx):
            if current_sum + token_array[i] > threshold:
                count += 1
            else:
                # Early break if we can't reach threshold anymore
                break
        return count, start_idx if count > 0 else -1
    
    if start_idx + remaining_depth > n:
        return 0, -1
    
    # More aggressive pruning using cumulative sums
    if start_idx + remaining_depth < n:
        best_possible = current_sum + min_remaining_sums[start_idx] - (
            min_remaining_sums[start_idx + remaining_depth] if start_idx + remaining_depth < n else 0
        )
        if best_possible <= threshold:
            return 0, -1
    
    count0 = 0
    last_valid_pointer = -1
    
    # Optimized loop bounds
    end_idx = min(n - remaining_depth + 1, n)
    
    # Main loop with early termination
    for pointer in range(start_idx, end_idx):
        new_sum = current_sum + token_array[pointer]
        
        # More aggressive early skip
        if new_sum + min_remaining_sums[pointer + 1] * (remaining_depth - 1) <= threshold:
            continue
            
        sub_count, sub_pointer = recursive_count(
            token_array,
            min_remaining_sums,
            threshold,
            pointer + 1,
            remaining_depth - 1,
            new_sum,
            valid_combinations
        )
        
        if sub_count == 0:
            # If no valid combinations found, later ones won't work either
            break
            
        count0 += sub_count
        last_valid_pointer = pointer
        
    return count0, last_valid_pointer

def count_n_wallets_threshold(wallet_df, wallet_types, threshold, n):
    token_array = get_token_array(wallet_df, wallet_types)
    
    # Pre-compute cumulative sums with better precision
    min_remaining_sums = np.zeros(len(token_array), dtype=np.float64)
    curr_sum = 0.0
    for i in range(len(token_array) - 1, -1, -1):
        curr_sum += token_array[i]
        min_remaining_sums[i] = curr_sum
    
    valid_combinations = np.empty(len(token_array), dtype=np.bool_)
    
    # Warmup run with small array
    if len(token_array) > 0:
        dummy_array = np.array([1.0], dtype=np.float64)
        dummy_sums = np.array([1.0], dtype=np.float64)
        recursive_count(
            dummy_array,
            dummy_sums,
            threshold,
            0,
            1,
            0.0,
            np.empty(1, dtype=np.bool_)
        )
    
    return recursive_count(
        token_array,
        min_remaining_sums,
        threshold,
        0,
        n,
        0.0,
        valid_combinations
    )

def count_distinct_first_wallets(group_df, wallet_types, threshold, k):
    token_array = get_token_array(group_df, wallet_types)
    n = len(token_array)
    distinct_first_wallets = 0
    
    # Iterate over possible starting indices for combinations of size k
    for start_idx in range(n - k + 1):
        # Calculate the sum of the current combination
        current_sum = np.sum(token_array[start_idx:start_idx + k])
        
        # If the sum is greater than or equal to the threshold, count this first wallet
        if current_sum >= threshold:
            distinct_first_wallets += 1
        else:
            # If the current sum is less than the threshold, no further combinations will meet the threshold
            break
    
    return distinct_first_wallets