from agents import *
from dealers import *
from evaluations import *

if __name__ == '__main__':  # for multiprocessing compatibility
    # Dealer objects
    openai = openai_dealer.Dealer(api_key='sk_brIgt2t3TLGjd0IFrWW9rw')
    pacman = pacman_dealer.Dealer(layout_representation='testClassic')
    native = native_dealer.Dealer()

    u_ro = uniform_rollout_agent.UniformRolloutAgent(depth=0, num_pulls=100)
    nested_u_ro = uniform_rollout_agent.UniformRolloutAgent(depth=2, num_pulls=10, policy=u_ro)

    e_ro = e_rollout_agent.ERolloutAgent(depth=1, num_pulls=10, epsilon=0.5)

    ucb_ro = ucb_rollout_agent.UCBRolloutAgent(depth=1, num_pulls=100, c=1.0)

    evaluation = rollout_evaluation.RolloutEvaluation(width=1, depth=10)
    ss_d2 = sparse_sampling_agent.SparseSamplingAgent(depth=2, pulls_per_node=20, evaluation=evaluation)
    ss_d5 = sparse_sampling_agent.SparseSamplingAgent(depth=5, pulls_per_node=5, evaluation=evaluation)

    uct = uct_agent.UCTAgent(depth=2, max_width=1, num_trials=1000, c=1)
    e_root_uct = e_root_uct_agent.ERootUCTAgent(depth=10, max_width=1, num_trials=1000, c=1)
    fsss = fsss_agent.FSSSAgent(depth=2, pulls_per_node=20, num_trials=1000)

    policy_set = [u_ro, e_ro]
    switch_agent = policy_switching_agent.PolicySwitchingAgent(depth=2, num_pulls=10, policies=policy_set)
    e_switch_agent = e_policy_switching_agent.EPolicySwitchingAgent(depth=10, num_pulls=10, policies=policy_set)

    all_agents = [u_ro, nested_u_ro, e_ro, ucb_ro, ss_d2, ss_d5, fsss, uct, e_root_uct, switch_agent, e_switch_agent]

    #openai.run_all(agents=[u_ro], multiprocess_mode='trials')

    #openai.run(agents=[u_ro], num_trials=1, env_name='FrozenLake-v0', multiprocess_mode='trial', show_moves=False, upload=False)

    #pacman.run(agents=[u_ro], num_trials=10, multiprocess_mode='trials')

    native.run(simulator_str='yahtzee', agents=[fsss, u_ro], num_trials=10, multiprocess_mode='trial', show_moves=False)



