import os

import psutil
from pympler import asizeof


def s_erase_history(params, substep, state_history, prev_state, policy_input):
    if prev_state["erase_history"] is True:
        idx = -2 if len(state_history) > 1 else -1

        for key, _ in state_history[idx][0].items():
            if key in [
                "actors",
                "lido",
                "dual_governance",
                "proposals",
                "non_initialized_proposals",
                "time_manager",
            ]:
                state_history[idx][0][key] = None

    return ("nothing", None)


def s_measure_history_bytes(params, substep, state_history, prev_state, policy_input):
    if prev_state["measure_memory"]:
        return ("history_bytes", asizeof.asizeof(state_history))
    else:
        return ("history_bytes", None)


def s_measure_all_state_bytes(params, substep, state_history, prev_state, policy_input):
    if prev_state["measure_memory"]:
        return ("state_bytes", asizeof.asizeof(prev_state))
    else:
        return ("state_bytes", None)


def s_measure_process_bytes(params, substep, state_history, prev_state, policy_input):
    if prev_state["measure_memory"]:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        used_bytes = memory_info.rss

        return ("process_bytes", used_bytes)
    else:
        return ("process_bytes", None)
