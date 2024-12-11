from scipy.stats import qmc


def precompute_lhs_samples(total_simulations, num_actors):
    # Create a Latin Hypercube sampler
    sampler = qmc.LatinHypercube(d=2)  # 2 dimensions: funds and reaction time

    # Generate samples
    samples = sampler.random(n=total_simulations)

    # Scale samples to actor indices
    samples[:, 0] *= num_actors  # Scale funds dimension
    samples[:, 1] *= num_actors  # Scale reaction time dimension

    return samples.astype(int)


print(precompute_lhs_samples(1000, 1804))
