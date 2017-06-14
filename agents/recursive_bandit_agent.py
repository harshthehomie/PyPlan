from abstract import absagent
from bandits import uniform_bandit_alg
from heuristics import zero_heuristic


class RecursiveBanditAgentClass(absagent.AbstractAgent):
    myname = "Recursive Bandit"

    def __init__(self, depth, pulls_per_node, heuristic=None, BanditClass=None, bandit_parameters=None):
        self.agentname = self.myname
        self.num_nodes = 1
        self.depth = depth
        self.pulls_per_node = pulls_per_node
        if heuristic is None:
            self.heuristic = zero_heuristic.ZeroHeuristicClass()
        else:
            self.heuristic = heuristic

        if BanditClass is None:
            self.BanditClass = uniform_bandit_alg.UniformBanditAlgClass
        else:
            self.BanditClass = BanditClass

        self.bandit_parameters = bandit_parameters

    def get_agent_name(self):
        return self.agentname

    """
    Selects the highest-valued action for the given state.
    """
    def select_action(self, state):
        self.num_nodes = 1
        (value, action) = self.estimateV(state, self.depth)
        return action

    """
    Returns the expected reward and action list for the current bandit.
    
    ~Walkthrough of structure for 2-action, 4-budget, 1-player, 2-depth uniform bandit
    estimateV(s0, 2):
        increment number of nodes 
        inherit bandit parameters, current player
        initialize Qvalues = [[0][0]] (2 actions)
        for i in [1,2,3,4] - pull budget
            select pull arm uniformly - 2 pulls per arm total
            take action denoted by arm and record immediate reward
            estimate future reward for depth=1 of this state (best action found by given bandit for horizon=depth-1=1)
            add future and immediate reward
            update current mean reward
        record best arm index
        return [q values for best arm, actions for best arm] 
    """
    def estimateV(self, state, depth):
        self.num_nodes += 1

        if depth == 0 or state.is_terminal():
            return self.heuristic.evaluate(state), None

        current_player = state.get_current_player()
        action_list = state.get_actions()
        num_actions = len(action_list)

        if self.bandit_parameters is None:
            bandit = self.BanditClass(num_actions)
        else:
            bandit = self.BanditClass(num_actions, self.bandit_parameters)

        current_state = state.clone()
        Qvalues = [[0]*state.number_of_players()]*num_actions

        # Use pull budget
        for i in range(self.pulls_per_node):
            chosen_arm = bandit.select_pull_arm()
            current_state.set(state)
            immediate_reward = current_state.take_action(action_list[chosen_arm])  # takes action on shared global state instead
            future_reward = self.estimateV(current_state, depth-1)[0]  # best arm's Q-value
            total_reward = [sum(r) for r in zip(immediate_reward, future_reward)]
            # append total rewards for arm to current Qvalues, for all players
            Qvalues[chosen_arm] = [sum(r) for r in zip(Qvalues[chosen_arm], total_reward)]
            # Update the current mean reward for the given arm
            bandit.update(chosen_arm, total_reward[current_player-1])

        # We've calculated Qvalues, so now we store best arm index
        best_arm_index = bandit.select_best_arm()

        return [q / bandit.get_num_pulls(best_arm_index) for q in Qvalues[best_arm_index]], action_list[best_arm_index]
