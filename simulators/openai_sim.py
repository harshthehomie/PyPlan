import logging
import copy

import itertools
import tabulate
import multiprocessing
import gym
import time
from gym import spaces
from gym import wrappers
from abstract import absstate, absagent


class OpenAIStateClass(absstate.AbstractState):
    """An interface to run bandit algorithms on the OpenAI environment library.

    The simulator can be found at https://github.com/openai/gym.

    Note that unlike other interfaces, this is not compatible with the dealer simulator due its reliance on the openAI
    engine.
    """

    def __init__(self, sim_name, api_key='', force=True):
        """Initialize an interface with the specified OpenAI simulation task and policy.

        :param sim_name: a valid env key that corresponds to a particular game / task.
        :param api_key: API key for uploading results to OpenAI Gym. Note that submissions are only scored if they are
            run for at least 100 trials.
        :param force: whether an existing directory at demos/OpenAI results/wrapper_target/ should be overwritten
        """
        self.api_key = api_key
        self.force = force
        self.resume = False  # whether to add data to the output directory
        self.show_moves = True
        self.agent = None

        self.sim_name = sim_name
        self.env = gym.make(sim_name)
        self.my_name = self.env.spec._env_name

        # output directory location for agent performance
        self.wrapper_target = 'OpenAI results\\' + self.sim_name[:-3]  # cut off version name
        self.env = wrappers.Monitor(self.env, self.wrapper_target, write_upon_reset=True, force=self.force,
                                    resume=self.resume)

        self.action_space = self.env.action_space
        if not isinstance(self.action_space, spaces.Discrete) and not isinstance(self.action_space, spaces.Tuple):
            raise Exception('Action space {} incompatible with {} (only supports Discrete and Tuple action spaces).'
                            .format(self.action_space, self))
        self.observation_space = self.env.observation_space

        self.original_observation = self.env.reset()  # initial observation
        self.current_observation = self.original_observation
        self.done = False  # indicates if the current observation is terminal

    def initialize(self):
        """Reinitialize the environment."""
        self.current_observation = self.env.reset()
        self.done = False

    def change_sim(self, sim_name):
        self.sim_name = sim_name
        self.env = gym.make(sim_name)
        self.my_name = self.env.spec._env_name

        # output directory location for agent performance
        self.wrapper_target = 'OpenAI results\\' + self.sim_name[:-3]  # cut off version name
        self.env = wrappers.Monitor(self.env, self.wrapper_target, write_upon_reset=True, force=self.force,
                                    resume=self.resume)

        self.action_space = self.env.action_space
        if not isinstance(self.action_space, spaces.Discrete) and not isinstance(self.action_space, spaces.Tuple):
            raise Exception('Action space {} incompatible with {} (only supports Discrete and Tuple action spaces).'
                            .format(self.action_space, self))
        self.observation_space = self.env.observation_space

        self.original_observation = self.env.reset()  # initial observation
        self.current_observation = self.original_observation
        self.done = False  # indicates if the current observation is terminal

    def run_all(self, agents, num_trials):
        """Runs the agents on all available simulators."""
        all_environments = gym.envs.registry.all()
        for env_idx, env in enumerate(all_environments):
            if should_skip(env.id):  # duplicate games / games that hang
                print("Unwanted game - skipping {}.".format(env.id))
                continue
            try:
                self.change_sim(env.id)
            except:  # If the action space is continuous
                print("Continuous action space - skipping {}.".format(env.id))
                continue
            self.run(agents=agents, num_trials=num_trials, multiprocess=False, show_moves=False)

    def run(self, agents, num_trials, multiprocess=True, show_moves=True, upload=False):
        """Run the given number of trials on the specified agents, comparing their performance.

        :param agents: the agents with which to run trials. Should be instances of AbstractAgent.
        :param num_trials: how many trials to be run.
        :param multiprocess: whether to use multiprocessing. NOTE: currently unsupported if a Monitor is instantiated.
        :param show_moves: if the environment can render, then render each move.
        """
        for agent in agents:
            agent = Agent(agent, self)
            if not isinstance(agent.policy, absagent.AbstractAgent):  # if this is an actual learning agent
                multiprocess = False
                logging.warning('Multiprocessing is disabled for agents which learn over multiple episodes.')
        if multiprocess:
            show_moves = False

        self.show_moves = show_moves

        table = []
        headers = ["Agent Name", "Average Episode Reward", "Success Rate", "Average Time / Move (s)"]

        for agent in agents:
            print('\nNow simulating: {}'.format(agent.agent_name))
            output = self.run_trials(agent, num_trials, multiprocess, upload)
            table.append([output['name'],  # agent name
                          output['average reward'],  # average final score
                          output['success rate'],  # win percentage
                          output['average move time']])  # average time taken per move
        print("\n" + tabulate.tabulate(table, headers, tablefmt="grid", floatfmt=".4f"))
        print("Each agent ran {} game{} of {}.".format(num_trials, "s" if num_trials > 1 else "", self.my_name))

    def run_trials(self, agent, num_trials=1, multiprocess=True, upload=False):
        """Run the given number of trials using the current configuration."""
        self.set_agent(agent)

        game_outputs = []
        if multiprocess:  # TODO: debug multiprocessing for wrappers
            self.resume = True
            # ensures the system runs smoothly
            pool = multiprocessing.Pool(processes=(multiprocessing.cpu_count() - 1))
            game_outputs = pool.map(self.run_trial, range(num_trials))
            self.resume = False  # done adding to the data
        else:
            for i in range(num_trials):
                game_outputs.append(self.run_trial(i))

        self.env.close()

        if upload and self.wrapper_target != '':
            print('Episode finished after {} timesteps.'.format(self.env.get_total_steps()))
            if self.api_key != '':
                gym.upload(self.wrapper_target, api_key=self.api_key)

        total_reward = 0
        wins = 0
        total_time = 0
        for output in game_outputs:
            total_reward += output['reward']
            wins += output['won']
            total_time += output['total time']

        return {'name': agent.agent_name, 'average reward': total_reward / num_trials,
                'success rate': wins / num_trials,
                'average move time': total_time / self.env.stats_recorder.total_steps}

    def run_trial(self, trial_num):
        """Using the game parameters, run and return total time spent selecting moves.

        :param trial_num: a placeholder parameter for compatibility with multiprocessing.Pool.
        """
        self.initialize()
        total_time = 0
        while self.done is False:
            begin = time.time()
            action = self.agent.act()
            total_time += time.time() - begin

            self.current_observation, reward, self.done, _ = self.env.step(action)

            if self.show_moves and 'human' in self.env.metadata['render.modes']:  # don't render if not supported
                self.env.render()  # TODO: fix certain invalid frames

        return {'reward': self.env.stats_recorder.rewards,
                'won': reward > 0,  # won if reward after game ends is positive
                'total time': total_time}

    def set_agent(self, agent):
        self.agent = Agent(agent, self)

    def clone(self):
        new_sim = copy.copy(self)  # QUESTION: deepcopy or copy?
        return new_sim

    def number_of_players(self):
        return 1

    def set(self, sim):
        self.env = copy.copy(sim.env.unwrapped)
        self.current_observation = sim.current_observation
        self.done = sim.done

    def is_terminal(self):
        return self.done

    def get_current_player(self):
        """Returns index of current player."""
        return 0

    def take_action(self, action):
        """Take the action and update the current state accordingly."""
        self.current_observation, reward, self.done, _ = self.env.step(action)  # QUESTION: current reward or total?
        rewards = [-1 * reward] * self.number_of_players()  # reward other agents get
        rewards[0] *= -1  # correct agent reward
        return rewards

    def get_actions(self):
        if isinstance(self.action_space, spaces.Discrete):
            return range(self.action_space.n)
        elif isinstance(self.action_space, spaces.Tuple):
            a_spaces = self.action_space.spaces
            ranges = tuple(tuple(range(s.n)) for s in a_spaces)  # TODO: take advantage of tuple aspect
            product = tuple(itertools.product(*ranges))  # return all combinations of action dimensions
            return product
        else:
            raise NotImplementedError

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash(self.current_observation)


class Agent(object):
    """An agent that interfaces between a policy and the OpenAI environment."""
    def __init__(self, policy, parent):
        self.policy = policy
        self.parent = parent  # pointer to the agent's parent structure

    def act(self):
        """Despite what its name may suggest, act only determines what action to take."""
        return self.policy.select_action(self.parent)


def should_skip(game_id):
    """Returns True if the game should be skipped."""
    skip_games = ["Assault", "BankHeist", "BeamRider-v4", "CliffWalking"]  # games take a very long time
    skip_keywords = ["Deterministic", "Frameskip", "ram"]
    for key in skip_games + skip_keywords:
        if str.find(game_id, key) != -1:
            return True
