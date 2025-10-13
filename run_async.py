from src.uni_async.model import UniAsyncModel


def run_async():
    NUM_AGENTS = 5
    MAX_TICKS = 200

    model = UniAsyncModel(NUM_AGENTS)
    print(f"--- Starting Asynchronous Leader Election with {NUM_AGENTS} agents ---")

    for t in range(MAX_TICKS):
        model.step()
        if model.all_finished():
            print(f"\n--- Protocol finished at tick {t} ---")
            break

    results = model.datacollector.get_agent_vars_dataframe()
    last = results.xs(t, level="Step")
    print("\nFinal state of all agents:\n", last)

    leaders = last["Leader"].dropna().unique()
    if len(leaders) == 1:
        print(f"\n✅ SUCCESS: Consensus reached. Leader is Agent {int(leaders[0])}.")
    else:
        print(f"\n❌ FAILURE: Multiple leaders detected: {leaders}")


if __name__ == "__main__":
    run_async()
