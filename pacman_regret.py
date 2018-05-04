import sys
# sys.path.append('/your/dir/to/tensorflow/models') # point to your tensorflow dir
import importlib
# from importlib import util
# spec = importlib.util.spec_from_file_location("agents", "../agents")
# foo = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(foo)
# foo.MyClass()

sys.path.append("../")

from PyPlan.agents import *
from dealers import pacman_dealer

"""
The UCB rollout agent attempts to minimize cumulative regret over its pull budget. Unlike uniform rollout, it doesn't 
spend much time on non-promising arms.
"""

if __name__ == '__main__':
    u_ro = uniform_rollout_agent.UniformRolloutAgent(depth=1, num_pulls=100)
    ucb_ro = ucb_rollout_agent.UCBRolloutAgent(depth=1, num_pulls=100, c=1.0)

    pacman = pacman_dealer.Dealer(layout_repr='testClassic')
    pacman.run(agents=[u_ro, ucb_ro], num_trials=15)
