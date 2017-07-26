import heapq
from abstract import abstract_agent


class FSSSAgentClass(abstract_agent.AbstractAgent):
    """A Forward Search Sparse Sampling agent, as described by Walsh et al."""
    my_name = "FSSS Agent"

    def __init__(self, depth, pulls_per_node, heuristic, discount=.5):
        self.agent_name = self.my_name

        self.depth = depth
        if depth < 1:
            raise Exception("Depth must be at least 1.")
        self.pulls_per_node = pulls_per_node
        self.discount = discount
        self.heuristic = heuristic

        self.num_nodes = 1
        self.discount_powers = [pow(self.discount, k) for k in range(self.depth)]  # pre-compute

    def get_agent_name(self):
        return self.agent_name

    def compute_value_bounds(self, value_bounds, depth):
        """Computes the value bounds based on reward information, accounting for depth and the discount factor."""
        if depth == 0:  # no more actions left to take
            return 0, 0

        if value_bounds['pre-computed min'] is not None:
            min_value = value_bounds['pre-computed min']
        else:
            minimums = [0] * depth
            temp = 0
            for i in range(depth):  # store result of losing at each step
                minimums[i] = temp + self.discount_powers[i] * value_bounds['defeat']
                temp += self.discount_powers[i] * value_bounds['min non-terminal']
            min_value = min(minimums)

        if value_bounds['pre-computed max'] is not None:
            max_value = value_bounds['pre-computed max']
        else:
            maximums = [0] * depth
            temp = 0
            for i in range(depth):  # store result of winning at each step
                maximums[i] = temp + self.discount_powers[i] * value_bounds['victory']
                temp += self.discount_powers[i] * value_bounds['max non-terminal']
            max_value = min(maximums)

        return min_value, max_value

    def select_action(self, state):
        """Selects the highest-valued action for the given state."""
        if state.is_terminal():  # there's nothing left to do
            return None

        self.num_nodes = 1

        root_node = Node(state, 0, state.get_actions())

        while True:
            self.run_trial(root_node, self.depth)
            if self.is_done(root_node):
                break

        return self.get_best_action(root_node)

    def run_trial(self, node, depth):
        """Each trial improves the accuracy of the bounds and closes one node.

        A node is closed when enough the lower and upper bounds on the state value Q(s) are equal.

        Each invocation involves the exploration of the s' with the largest state value bound discrepancy for the a with
         the greatest upper bound, and ends with the closure of one new node in the tree. The selection of a* and s*
         allows for pruning compared to Sparse Sampling. That is, if an action at the root node level looks good enough,
         we don't need to keep closing nodes in suboptimal parts of the tree; we can just make our decision.

        :param node: points to a Node object.
        :param depth: how many more layers to generate before using the heuristic.
        """
        if node.state.is_terminal():
            node.lower_state = node.transition_reward
            node.upper_state = node.transition_reward
            return

        min_value, max_value = self.compute_value_bounds(node.state.get_value_bounds(), depth)

        current_player = node.state.get_current_player()

        if depth == 0:  # reached a leaf
            state_value = self.heuristic.evaluate(node.state)
            node.lower_state = state_value[current_player]
            node.upper_state = state_value[current_player]
            return
        elif node.times_visited == 0:
            for action_idx in range(node.num_actions):
                heapq.heappush(node.lower, (-1 * min_value, action_idx))
                heapq.heappush(node.upper, (-1 * max_value, action_idx))

        best_action = self.get_best_action(node)
        best_action_idx = node.action_list.index(best_action)
        if node.action_expansions[best_action_idx] < self.pulls_per_node:  # if we have pulls remaining
            i = 0  # expand scope of i
            for i in range(self.pulls_per_node - node.action_expansions[best_action_idx]):  # sample C - n_{sda*} states
                sim_state = node.state.clone()  # clone so that hashing works properly
                immediate_reward = sim_state.take_action(best_action)  # simulate taking action

                if sim_state not in node.children[best_action_idx]:
                    new_node = Node(sim_state, immediate_reward[current_player], sim_state.get_actions())
                    new_node.lower_state = min_value
                    new_node.upper_state = max_value

                    node.children[best_action_idx][sim_state] = new_node
                    self.num_nodes += 1  # we've made a new Node
                    break  # we break early since a new child state means it has the greatest bound difference
            node.action_expansions[best_action_idx] += i + 1  # account for 0-indexing

        child_nodes = [node.children[best_action_idx][n] for n in node.children[best_action_idx]]

        # Find the greatest difference between the upper and lower bounds for depth-1
        bound_differences = [tuple([n.state, n.upper_state - n.lower_state]) for n in child_nodes]
        successor_key = (max(bound_differences, key=lambda x: x[1]))[0]  # retrieve key from tuple
        successor_node = node.children[best_action_idx][successor_key]

        self.run_trial(successor_node, depth - 1)

        node.times_visited += 1

        # Bounds for best action in this state are the reward plus the discounted average of child bounds
        new_lower = successor_node.transition_reward + self.discount * sum([n.lower_state for n in child_nodes]) \
                                                                      / node.action_expansions[best_action_idx]
        heapq.heapreplace(node.lower, (-1 * new_lower, best_action_idx))  # pop the old best_action_idx lower; push new

        new_upper = successor_node.transition_reward + self.discount * sum([n.upper_state for n in child_nodes]) \
                                                                      / node.action_expansions[best_action_idx]
        heapq.heapreplace(node.upper, (-1 * new_upper, best_action_idx))

        node.lower_state = -1 * node.lower[0][0]  # [list_pos][value]; correct for heap inversion
        node.upper_state = -1 * node.upper[0][0]

    @staticmethod
    def is_done(root_node):
        """Returns whether we've found the best action at the root state.

        Specifically, this is the case when the lower bound for the best action is greater than the upper bounds of all
            non-best actions.
        """
        # Question what if we only have 1 action here?
        best_lower = root_node.lower[0]  # largest (after inversion) lower bound in the heap
        best_upper = heapq.nsmallest(2, root_node.upper)  # two largest (after inversion) upper bounds
        if best_lower[1] == best_upper[0][1]:  # don't want to compare best_lower with its own upper bound
            return best_lower[0] <= best_upper[1][0]  # compare to second-best
        else:
            return best_lower[0] <= best_upper[0][0]

    @staticmethod
    def get_best_action(node):
        """Returns the action with the maximal upper bound for the given node.state and depth."""
        best_upper = node.upper[0]
        return node.action_list[best_upper[1]]


class Node:
    """Stores information on a state, reward for reaching the state, and the actions available"""

    def __init__(self, state, transition_reward, action_list):
        """Contains the state, reward obtained by reaching the state, actions at the state, children, and bounds."""
        self.state = state
        self.transition_reward = transition_reward
        self.action_list = action_list
        self.num_actions = len(self.action_list)

        self.num_nodes = 0
        self.times_visited = 0

        """
        Each action is associated with a dictionary that stores successor nodes.
        The key for each successor is the state.
        """
        self.children = [{} for _ in range(self.num_actions)]

        """
        The lower and upper bounds on the estimate Q^d(s, a) of the value of taking action a in state s at depth d. 
        
        Stored as tuples (-1*bound_value, action_idx) in a heap. Values are inverted for easier modification via heapq.
        """
        self.lower = []
        self.upper = []

        # Bounds on the state value
        self.lower_state = float('-inf')
        self.upper_state = float('inf')

        # action_expansions[action_idx] = how many times we've sampled the given action
        self.action_expansions = [0] * self.num_actions