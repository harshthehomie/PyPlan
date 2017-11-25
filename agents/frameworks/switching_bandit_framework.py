import numpy as np
import multiprocessing
from abstract import abstract_agent
from agents.bandits import uniform_bandit


class SwitchingBanditFramework(abstract_agent.AbstractAgent):
    """An agent that takes a list of policies and returns the value of the best one at a given state."""
    name = "Policy-Switching Bandit Agent"

    def __init__(self, depth, pulls_per_node, policies, bandit_class=None, bandit_parameters=None, multiprocess=False):
        """Initialize a policy-switching bandit that follows each selected policy for depth steps per trajectory."""
        self.num_nodes = 1

        self.depth = depth
        self.pulls_per_node = pulls_per_node

        self.policies = policies

        self.bandit_class = bandit_class if bandit_class else uniform_bandit.UniformBandit
        self.bandit_parameters = bandit_parameters

        self.set_multiprocess(multiprocess)

    def set_multiprocess(self, multiprocess):
        """Change the multiprocess parameter."""
        self.multiprocess = multiprocess
        if self.multiprocess:
            for policy in self.policies:
                if hasattr(policy, 'set_multiprocess'):
                        policy.set_multiprocess(False)

    def select_action(self, state):
        """Selects the highest-valued action for the given state."""
        self.num_nodes = 1
        return self.estimateV(state)[1]  # return the best action

    def estimateV(self, state):
        """Returns the best expected reward and action selected by the best policy at the given state."""
        self.num_nodes += 1

        num_policies = len(self.policies)
        bandit = self.bandit_class(num_policies, self.bandit_parameters) if self.bandit_parameters \
            else self.bandit_class(num_policies)

        # For each policy, for each player, initialize a q-value
        q_values = np.array([[0.0] * state.num_players for _ in range(num_policies)])

        if self.multiprocess:
            with multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1) as pool:
                remaining = self.pulls_per_node
                while remaining > 0:
                    pulls_to_use = min(pool._processes, remaining)
                    outputs = pool.starmap(self.run_pull, [[state, bandit]] * pulls_to_use)
                    remaining -= pulls_to_use

                    for arm_data in outputs:
                        policy_idx, total_reward = arm_data
                        q_values[policy_idx] += total_reward
                        bandit.update(policy_idx, total_reward[state.current_player])
        else:
            for _ in range(self.pulls_per_node):  # use pull budget
                arm_data = self.run_pull(state, bandit)

                # Integrate total reward with current q_values
                policy_idx, total_reward = arm_data
                q_values[policy_idx] += total_reward
                bandit.update(policy_idx, total_reward[state.current_player])  # update the reward for the given arm

        # Get most-selected action of highest-valued policy (useful for stochastic environments)
        best_policy_idx = bandit.select_best_arm()
        best_action_select = self.policies[best_policy_idx].select_action(state)

        return q_values[best_policy_idx] / bandit.num_pulls[best_policy_idx], best_action_select

    def run_pull(self, state, bandit):
        """Choose an arm to pull, execute the action, and return the chosen arm and total reward received."""
        # Select a policy
        policy_idx = bandit.select_pull_arm()
        policy = self.policies[policy_idx]

        sim_state = state.clone()
        total_reward = np.array([0.0] * state.num_players)  # calculate discounted total rewards
        for _ in range(self.depth):
            if sim_state.is_terminal():
                break
            action = policy.select_action(sim_state)
            total_reward += sim_state.take_action(action)

        return [policy_idx, total_reward]

