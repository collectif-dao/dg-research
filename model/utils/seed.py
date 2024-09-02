from numpy.random import Generator, default_rng

rng: Generator = None


def initialize_seed(seed):
    global rng
    rng = default_rng(seed)


def get_rng() -> Generator:
    if rng is None:
        raise ValueError("Random number generator is not initialized. Call initialize_rng first.")
    return rng
