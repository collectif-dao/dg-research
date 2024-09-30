from hypothesis import given
from hypothesis import strategies as st

from specs.escrow.withdrawal_batches import Status, WithdrawalsBatchesQueue
from specs.types.sequential_batches import SequentialBatches

sequential_integers = (
    st.lists(st.integers(min_value=1, max_value=1000), min_size=1)
    .map(sorted)
    .filter(lambda lst: all(lst[i] + 1 == lst[i + 1] for i in range(len(lst) - 1)))
)


@given(
    min_request_amount=st.integers(min_value=1, max_value=1000),
    request_amount=st.integers(min_value=1, max_value=1000),
    amount=st.integers(min_value=1, max_value=100000),
)
def test_calc_request_amounts(min_request_amount, request_amount, amount):
    queue = WithdrawalsBatchesQueue()
    request_amounts = queue.calc_request_amounts(min_request_amount, request_amount, amount)

    if len(request_amounts) > 1:
        assert request_amounts[-1] == amount % request_amount or request_amounts[-1] == request_amount

    for i in range(len(request_amounts) - 1):
        assert request_amounts[i] == request_amount


@given(unstETH_ids=sequential_integers)
def test_add_sequential_unstETH_ids(unstETH_ids):
    queue = WithdrawalsBatchesQueue()

    if queue.state.status != Status.Opened:
        queue.open()

    existing_unstETH_ids = queue.state.total_unstETH_count
    existing_batches = len(queue.state.batches)
    sorted_unstETH_ids = sorted(unstETH_ids)

    for i in range(len(sorted_unstETH_ids) - 1):
        assert sorted_unstETH_ids[i] == sorted_unstETH_ids[i]

    last_batch_index = len(queue.state.batches) - 1
    last_withdrawals_batch = queue.state.batches[last_batch_index]
    new_withdrawals_batch = SequentialBatches.create(unstETH_ids[0], len(unstETH_ids))

    merged = SequentialBatches.can_merge(last_withdrawals_batch, new_withdrawals_batch)

    queue.add(sorted_unstETH_ids)

    assert queue.state.total_unstETH_count == len(sorted_unstETH_ids) + existing_unstETH_ids

    last_batch_id = existing_batches + (0 if merged else 1)

    assert len(queue.state.batches) == last_batch_id
    if not merged:
        assert queue.state.batches[existing_batches].size() == len(sorted_unstETH_ids)


@given(max_unstETH_ids_count=st.integers(min_value=1, max_value=100))
def test_claim_next_batch(max_unstETH_ids_count):
    queue = WithdrawalsBatchesQueue()
    if queue.state.status != Status.Opened:
        queue.open()

    unstETH_ids = list(range(100))
    queue.add(unstETH_ids)

    last_claimed = queue.state.total_unstETH_claimed

    claimed_ids = queue.claim_next_batch(max_unstETH_ids_count)

    assert queue.state.total_unstETH_claimed == last_claimed + len(claimed_ids)
    assert len(claimed_ids) <= max_unstETH_ids_count
