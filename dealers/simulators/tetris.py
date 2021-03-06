import copy
import numpy as np
import random
from abstract import abstract_state


class TetrisState(abstract_state.AbstractState):
    env_name = "Tetris"
    num_players = 1
    original_state = {
            "current_board": [[0] * 10 for _ in range(20)],
            "current_piece": None,
            "next_piece": None
        }

    def __init__(self):
        self.current_state = self.original_state
        self.current_state["current_piece"] = random.randrange(1, 6)
        self.current_state["next_piece"] = random.randrange(1, 6)

        self.game_outcome = None
        self.game_over = False

    def clone(self):
        return copy.deepcopy(self)

    def set(self, sim):
        self.current_state = copy.deepcopy(sim.current_state)
        self.game_outcome = sim.game_outcome
        self.game_over = sim.game_over

    def reinitialize(self):
        self.current_state = copy.deepcopy(self.original_state)
        self.current_state["current_piece"] = random.randrange(1, 6)
        self.current_state["next_piece"] = random.randrange(1, 6)
        self.game_outcome = None
        self.game_over = False

    def get_value_bounds(self):
        return {'defeat': 0, 'min non-terminal': 5,
                'victory': 0, 'max non-terminal': 55,
                'pre-computed min': None, 'pre-computed max': None,
                'evaluation function': None}

    def take_action(self, action):
        x_position = action['position'][0]
        y_position = action['position'][1]
        piece = self.get_piece_shape(action['piece_number'], action['rot_number'])
        current_board = self.current_state['current_board']

        if piece is None:
            raise ValueError("Invalid rotation number.")

        # INSERT THE PIECE
        for x in range(len(piece)):
            for y in range(len(piece[0])):
                current_board[x_position + x][y_position + y] = piece[x][y]

        reward = [5.0] * self.num_players

        # UPDATE THE BOARD
        for x in range(19, -1, -1):
            hit = True
            for y in range(10):
                if current_board[x][y] == 0:
                    hit = False
                    break
            if hit:
                reward[self.num_players - 1] += 10.0
                for subx in range(x, -1, -1):
                    if subx == 0:
                        current_board[subx] = [0] * 10
                    else:
                        current_board[subx] = current_board[subx - 1]

        return np.array(reward)

    def get_actions(self):
        actions_list = []
        current_board = self.current_state["current_board"]
        current_piece_num = self.current_state["current_piece"]
        board_height = len(current_board)
        board_width = len(current_board[0])

        for rot_num in range(0, 4):
            piece_shape = self.get_piece_shape(current_piece_num, rot_num)
            if piece_shape is not None:
                piece_width = len(piece_shape[0])
                piece_height = len(piece_shape)
                for y in range(10):
                    if y > (board_width - piece_width):
                        break
                    for x in range(20):
                        # CHECK FOR WHEN PIECE IS PUT IN EMPTY BOARD
                        if x == (board_height - piece_height):
                            if current_board[x][y] == 0:
                                action = {'position': [x, y], 'piece_number': current_piece_num, 'rot_number': rot_num}
                                actions_list.append(action)
                                break
                        else:
                            if current_board[x][y] == 1:
                                break
                            # CHECK IF THE PIECE CAN BE PLACED AT THIS TOP LEFT POSITION
                            # WITH AT LEAST ONE PIECE IN ITS BOTTOM TO HOLD IT.
                            hold = False
                            for btm in range(piece_width):
                                x_check = 1
                                while piece_shape[piece_height - x_check][btm] == 0:
                                    x_check += 1

                                if piece_shape[piece_height - x_check][btm] == 1:
                                    if current_board[x + piece_height - (x_check - 1)][y + btm] == 1:
                                        hold = True
                                        break

                            if hold:
                                # Collision check
                                collision = False
                                for subx in range(piece_height):
                                    for suby in range(piece_width):
                                        if piece_shape[subx][suby] == 1:
                                            if current_board[x + subx][y + suby] == 1:
                                                collision = True
                                                break
                                    if collision:
                                        break

                                if collision is False:
                                    action = {'position': [x, y], 'piece_number': current_piece_num,
                                              'rot_number': rot_num}
                                    actions_list.append(action)
                                    hit = True
                                break
        return actions_list

    def is_terminal(self):
        return len(self.get_actions()) == 0

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash(str(self.current_state["current_board"]))

    def __str__(self):
        output = ''
        for x in range(20):
            output += str(self.current_state["current_board"][x]) + "\n"

        return output

    def change_turn(self):
        self.current_state["current_piece"] = int(self.current_state["next_piece"])
        self.current_state["next_piece"] = random.randrange(1, 6)
        self.game_over = self.is_terminal()

    # Tetris-specific function
    @staticmethod
    def get_piece_shape(piece_number, rotation_number=0):
        piece = None

        if piece_number == 1:
            if rotation_number == 0:
                piece = [[1, 1], [1, 0]]
            elif rotation_number == 1:
                piece = [[1, 1], [0, 1]]
            elif rotation_number == 2:
                piece = [[0, 1], [1, 1]]
            elif rotation_number == 3:
                piece = [[1, 0], [1, 1]]
        elif piece_number == 2:
            if rotation_number == 0:
                piece = [[1], [1], [1]]
            elif rotation_number == 1:
                piece = [[1, 1, 1]]
        elif piece_number == 3:
            if rotation_number == 0:
                piece = [[0, 1, 0], [1, 1, 1]]
            elif rotation_number == 1:
                piece = [[1, 0], [1, 1], [1, 0]]
            elif rotation_number == 2:
                piece = [[1, 1, 1], [0, 1, 0]]
            elif rotation_number == 3:
                piece = [[0, 1], [1, 1], [0, 1]]
        elif piece_number == 4:
            if rotation_number == 0:
                piece = [[1, 1], [1, 1]]
        elif piece_number == 5:
            if rotation_number == 0:
                piece = [[0, 1, 1], [1, 1, 0]]
            elif rotation_number == 1:
                piece = [[1, 0], [1, 1], [0, 1]]
        elif piece_number == 6:
            if rotation_number == 0:
                piece = [[1, 1, 0], [0, 1, 1]]
            elif rotation_number == 1:
                piece = [[0, 1], [1, 1], [1, 0]]

        return piece
