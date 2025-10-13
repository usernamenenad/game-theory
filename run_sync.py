from src.uni_sync.model import UniSyncModel


def run_sync():
    NUM_AGENTS = 5
    MAX_STEPS = NUM_AGENTS * 5

    model = UniSyncModel(NUM_AGENTS)

    print(f"--- Starting Leader Election with {NUM_AGENTS} agents ---")
    step_count = 0

    for i in range(MAX_STEPS):
        if model.all_agents_finished():
            print(f"\n--- Protocol finished at step {i} ---")
            break

        model.step()
        step_count += 1

    results = model.datacollector.get_agent_vars_dataframe()
    final_step_results = results.xs(step_count, level="Step")
    print("Final State of all Agents:")
    print(final_step_results)

    # Verify consensus
    leaders = final_step_results["Leader"].dropna().unique()
    if len(leaders) == 1:
        print(
            f"\nSUCCESS: All agents agree that the leader is Agent {int(leaders[0])}."
        )
    else:
        print(f"\nFAILURE: Agents did not reach consensus. Leaders found: {leaders}.")


if __name__ == "__main__":
    run_sync()
