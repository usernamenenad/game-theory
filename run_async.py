from src.uni_async.model import UniAsyncModel


def run_async():
    NUM_AGENTS = 5
    NUM_MALICIOUS_AGENTS = 1
    MAX_TICKS = 200

    model = UniAsyncModel(N=NUM_AGENTS, malicious_nodes=NUM_MALICIOUS_AGENTS)
    print(f"--- Starting Asynchronous Leader Election with {NUM_AGENTS} agents ---")

    for t in range(MAX_TICKS):
        model.step()
        if model.all_finished():
            print(f"\n--- Protocol finished at tick {t} ---")
            break

    results = model.datacollector.get_agent_vars_dataframe()
    last = results.xs(t, level="Step")
    print("\nFinal state of all agents:\n", last)

    leaders = last["Leader"]

    all_non_nan = leaders.notna().all()
    unique_leaders = leaders.dropna().unique()

    if all_non_nan and len(unique_leaders) == 1:
        print(
            f"\n[System] ✅ SUCCESS: Consensus reached. Leader is Agent {int(unique_leaders[0])}."
        )
    else:
        print(f"\n[System] ❌ FAILURE.")


if __name__ == "__main__":
    run_async()
