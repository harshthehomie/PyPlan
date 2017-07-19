from agents import rollout_agent
from bandits import ucb_bandit_alg


class UCBRolloutAgentClass(rollout_agent.RolloutAgentClass):
    my_name = "UCB Rollout Agent"

    def __init__(self, depth, num_pulls, c, policy=None):
        rollout_agent.RolloutAgentClass.__init__(self, depth=depth, num_pulls=num_pulls,
                                                 policy=policy,
                                                 bandit_class=ucb_bandit_alg.UCBBanditAlgClass,
                                                 bandit_parameters=c)

        self.agent_name = self.my_name + " (d={}, n={}, c={})".format(depth, num_pulls, c)
