import datetime

from reconchess import *
import chess.engine
import os
import random

STOCKFISH_ENV_VAR = 'STOCKFISH_EXECUTABLE'
stockfish_path = os.environ[STOCKFISH_ENV_VAR]


def is_edge_square(square):
    row, col = square // 8, square % 8
    return row in (0, 7) or col in (0, 7)


def check_valid_state(board, sensed_tiles):
    match = True
    for square, piece in sensed_tiles:
        if board.piece_at(square) is None and piece is None:
            continue
        if board.piece_at(square) is not None and piece is not None and board.piece_at(
                square).symbol() == piece.symbol():
            continue
        match = False
        break
    return match


class ImprovedAgent(Player):

    def __init__(self):
        self.opponent_king_position = None
        self.board = None
        self.color = None
        self.start = False
        self.possible_states = set()
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True, timeout=None)
        self.start_time = None
        self.end_time = None
        self.opp_king_captured = False
        self.my_piece_captured_square = None
        self.move_num = 0
        self.opp_king_not_sensed = True

    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.board = board
        self.color = color
        if color:
            self.start = True
        self.start_time = datetime.datetime.now()
        self.opponent_king_position = board.king(not self.color)

        # self.possible_states.add(board.fen())
        initial_state = board.fen()
        self.possible_states.add(initial_state)

    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[Square]):
        print("handle_opponent_move_result(start): ", len(self.possible_states))

        if self.start:
            self.start = False
            return

        # new_states = set()

        if captured_my_piece:
            new_states = self.generate_next_positions_with_capture(capture_square)
            self.my_piece_captured_square = capture_square
            print("opp capture")
        else:
            new_states = self.generate_next_positions()
            self.my_piece_captured_square = None
            print("opp no capture")

        if not new_states:
            new_states = self.possible_states

        self.possible_states = new_states

        print("handle_opponent_move_result(end): ", len(self.possible_states))

    def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> \
    Optional[Square]:
        # Filter out edge squares
        sense_actions = [square for square in sense_actions if not is_edge_square(square)]

        if not sense_actions:
            return None

        coin = random.randint(1, 100)
        if self.opp_king_captured:
            square_to_return = self.opp_king_captured
            if coin > 80:
                square_to_return += 1
            else:
                square_to_return -= 1
            self.opp_king_captured = False
            return square_to_return

        if self.my_piece_captured_square:
            return self.my_piece_captured_square

        # Scoring function for sense actions
        sense_scores = {action: 0 for action in sense_actions}

        for state in self.possible_states:
            board = chess.Board(state)

            # Prioritize sensing near opponent's King
            if coin > 90:
                if self.opponent_king_position:
                    for square in sense_actions:
                        king_distance = chess.square_distance(self.opponent_king_position, square)
                        sense_scores[square] += 8 - king_distance

            # Add more heuristics here, e.g., sensing near known opponent pieces
            # Increase score for sensing near opponent pieces
            for piece_type in range(1, 7):
                for piece in board.pieces(piece_type, not self.color):
                    for square in sense_actions:
                        piece_distance = chess.square_distance(piece, square)
                        sense_scores[square] += 6 - piece_distance  # Example heuristic

        # Choose the sense action with the highest score
        best_sense = max(sense_scores, key=sense_scores.get)

        if not best_sense:
            print("pain")
            return random.choice(sense_actions)

        return best_sense

    # def choose_sense(self, sense_actions: List[Square], move_actions: List[chess.Move], seconds_left: float) -> Square:
    #     # Filter out sense actions on the board's edge
    #     sense_actions = [square for square in sense_actions if not is_edge_square(square)]
    #
    #     coin = random.randint(0, 100)
    #
    #     # Increase sensing towards the opponent's side for the first four runs
    #     if self.move_num <= 4:
    #         opponent_color = not self.color
    #         opponent_side_start = 56 if opponent_color == chess.WHITE else 0
    #         opponent_side_end = 63 if opponent_color == chess.WHITE else 7
    #         opponent_side_squares = [i for i in range(opponent_side_start, opponent_side_end + 1)]
    #         middle_opponent_side = [square for square in opponent_side_squares if square in sense_actions]
    #         if coin < 50 and middle_opponent_side:
    #             return random.choice(middle_opponent_side)
    #
    #     # If the opponent king is captured, prioritize looking in the enemy territory for the king
    #     if self.opp_king_captured:
    #         square_to_return = self.opp_king_captured
    #         if coin > 80:
    #             square_to_return += 1
    #         else:
    #             square_to_return -= 1
    #         self.opp_king_captured = False
    #         return square_to_return
    #
    #     # Sense if our piece was captured
    #     if self.my_piece_captured_square:
    #         return self.my_piece_captured_square
    #
    #     # Iterate through all possible states
    #     for state in self.possible_states:
    #         board = chess.Board(state)
    #         enemy_king_square = board.king(not self.color)
    #
    #         # Since castling doesn't really happen much in the first six moves,
    #         # only start with this process after 6 moves
    #         if self.move_num == 6 and (enemy_king_square == 60 or enemy_king_square == 4) and coin < 65:
    #             return 52 if enemy_king_square == 60 else 13
    #         if self.move_num > 6 and (enemy_king_square == 60 or enemy_king_square == 4) and coin < 65:
    #             return enemy_king_square + 1 - 8 if enemy_king_square == 60 else enemy_king_square + 9
    #         elif self.opp_king_captured is True:
    #             print("PLEASE KILL ME")
    #             if coin < 60:
    #                 return 62 - 8 if self.color == chess.BLACK else 6 + 8
    #             else:
    #                 return 58 - 8 if self.color == chess.BLACK else 2 + 8
    #
    #         # 25% of the time, check our own king safety
    #         if 65 <= coin <= 90:
    #             my_king_square = board.king(self.color)
    #             return my_king_square + 8 if self.color == chess.WHITE else my_king_square - 8
    #
    #     # Otherwise, just randomly choose a sense action, but don't sense on a square where our pieces are located
    #     for state in self.possible_states:
    #         board = chess.Board(state)
    #         for square, piece in board.piece_map().items():
    #             if piece.color == self.color and square in sense_actions:
    #                 sense_actions.remove(square)
    #
    #     # Return a random valid sense action
    #     return random.choice(sense_actions)

    def handle_sense_result(self, sense_result: List[Tuple[Square, Optional[chess.Piece]]]):

        new_possible_states = set()
        print("handle_sense_result(start): ", len(self.possible_states))

        # Update the position of the opponent's king if it was sensed
        for square, piece in sense_result:
            if piece and piece.piece_type == chess.KING and piece.color != self.color:
                self.opponent_king_position = square
                break

        for state in self.possible_states:
            board = chess.Board(state)
            valid_state = True
            for square, piece in sense_result:
                if board.piece_at(square) is None and piece is not None:
                    valid_state = False
                    break
                elif board.piece_at(square) is not None and piece is None:
                    valid_state = False
                    break
                elif board.piece_at(square) is not None and piece is not None:
                    if board.piece_at(square).piece_type != piece.piece_type:
                        valid_state = False
                        break
                    if board.piece_at(square).color != piece.color:
                        valid_state = False
                        break
            if valid_state:
                new_possible_states.add(state)

        self.possible_states = new_possible_states
        print("handle_sense_result(end): ", len(self.possible_states))

    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        print('choose_move(start):', len(self.possible_states))

        if len(self.possible_states) > 10000:
            print("limiting")
            self.possible_states = set(random.sample(list(self.possible_states), 10000))

        move_frequency = {}
        run_time = 10.0 / len(self.possible_states) if len(self.possible_states) > 0 else 10.0

        for state in self.possible_states:
            board = chess.Board(state)
            enemy_king_square = board.king(not self.color)
            if enemy_king_square:
                enemy_king_attackers = board.attackers(self.color, enemy_king_square)
                if enemy_king_attackers:
                    attacker_square = enemy_king_attackers.pop()
                    attacking_move = chess.Move(attacker_square, enemy_king_square)
                    if attacking_move in move_actions:
                        return attacking_move

        for state in self.possible_states:
            board = chess.Board(state)
            if board.status() == chess.STATUS_VALID:
                try:
                    board.clear_stack()
                    result = self.engine.play(board, chess.engine.Limit(time=run_time))
                    if result.move in move_frequency:
                        move_frequency[result.move] += 1
                    else:
                        move_frequency[result.move] = 1
                except (chess.engine.EngineTerminatedError, chess.engine.EngineError):
                    self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True, timeout=None)

        sorted_moves = sorted(move_frequency, key=move_frequency.get, reverse=True)
        valid_moves = [move for move in sorted_moves if move in move_actions]

        print('valid moves:', len(valid_moves))

        return valid_moves[0] if valid_moves else random.choice(move_actions)

    def is_attack_on_opponent_king(self, move: chess.Move) -> bool:
        for state in self.possible_states:
            board = chess.Board(state)
            board.push(move)
            if board.is_checkmate():
                return True
        return False

    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[Square]):
        print("handle_move_result(start): ", len(self.possible_states))

        print("requested", requested_move)
        print("taken", taken_move)

        # updated_possible_states = set()
        #
        # if taken_move is not None and captured_opponent_piece:
        #     print("capt")
        #     for state in self.possible_states:
        #         board = chess.Board(state)
        #         try:
        #             if captured_opponent_piece:
        #                 if board.is_capture(taken_move) and taken_move.to_square == capture_square and taken_move in board.pseudo_legal_moves:
        #                     new_board = board.copy()
        #                     new_board.push(taken_move)
        #                     updated_possible_states.add(new_board.fen())
        #         except ValueError:
        #             # This state is invalid, so we skip it
        #             pass
        # elif taken_move is not None and not captured_opponent_piece:
        #     print("no capt")
        #     for state in self.possible_states:
        #         board = chess.Board(state)
        #         if taken_move in board.pseudo_legal_moves:
        #             new_board = board.copy()
        #             new_board.push(taken_move)
        #             updated_possible_states.add(new_board.fen())
        # else:
        #     print('booboo')
        #     for state in self.possible_states:
        #         board = chess.Board(state)
        #         if requested_move not in board.pseudo_legal_moves:
        #             updated_possible_states.add(state)
        #
        # self.possible_states = updated_possible_states

        self.possible_states = self.move_result_states(requested_move, taken_move, captured_opponent_piece, capture_square, self.possible_states)

        self.move_num += 1
        print("handle_move_result(end): ", len(self.possible_states))
        # print("handle_move_result(end): ", len(self.possible_states))

    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        try:
            # if the engine is already terminated then this call will throw an exception
            self.engine.quit()
            self.end_time = datetime.datetime.now()
            game_duration = self.end_time - self.start_time
            minutes, seconds = divmod(game_duration.total_seconds(), 60)
            print(f"Game Duration: {int(minutes)} minutes {int(seconds)} seconds")

        except chess.engine.EngineTerminatedError:
            pass

    def generate_next_positions(self):

        next_positions = set()

        for state in self.possible_states:
            board = chess.Board(state)

            possible_moves = list(board.pseudo_legal_moves) + [chess.Move.null()]

            next_positions.update(self.get_opponent_castling(board))

            for move in possible_moves:
                if board.piece_at(move.to_square) is None:
                    new_board = board.copy()
                    new_board.push(move)
                    next_positions.add(new_board.fen())

        print("next_positions no capture:", len(next_positions))

        return next_positions

    def get_opponent_castling(self, board):

        castling = set()

        if board.has_kingside_castling_rights(not self.color):
            king = board.king(not self.color)
            square = chess.square(chess.square_file(king) + 2, chess.square_rank(king))
            move = chess.Move(king, square)
            new_board = board.copy()
            new_board.push(move)
            castling.add(new_board.copy().fen())

        if board.has_queenside_castling_rights(not self.color):
            king = board.king(not self.color)
            square = chess.square(chess.square_file(king) - 2, chess.square_rank(king))
            move = chess.Move(king, square)
            new_board = board.copy()
            new_board.push(move)
            castling.add(new_board.copy().fen())

        return castling

    def generate_next_positions_with_capture(self, capture_square):
        next_positions = set()
        for state in self.possible_states:
            board = chess.Board(state)
            possible_moves = list(board.pseudo_legal_moves)
            for move in possible_moves:
                if board.is_capture(move) or board.is_en_passant(move):
                    new_board = board.copy()
                    new_board.push(move)
                    # if board.piece_at(capture_square) is None or board.piece_at(capture_square).color != self.color:
                    next_positions.add(new_board.fen())

        print("next_positions capture:", len(next_positions))

        return next_positions

    def move_result_states(self, requested_move, taken_move, captured_opponent_piece, capture_square, possible_states):
        new_boards = set()
        for state in possible_states:
            board = chess.Board(state)
            if board.turn != self.color:
                board.turn = self.color

            if taken_move is not None:
                if taken_move in board.pseudo_legal_moves:
                    if captured_opponent_piece and board.piece_at(capture_square) is not None and board.piece_at(
                            capture_square).piece_type != chess.KING:
                        board.push(taken_move)
                        new_boards.add(board.fen())
                    elif not captured_opponent_piece and board.piece_at(taken_move.to_square) is None:
                        board.push(taken_move)
                        new_boards.add(board.fen())

            elif requested_move:
                if board.piece_at(requested_move.from_square) is not None and board.piece_at(
                        requested_move.from_square).piece_type == chess.PAWN:
                    if board.piece_at(requested_move.to_square) is None and chess.square_file(
                            requested_move.from_square) != chess.square_file(requested_move.to_square):
                        new_boards.add(state)
                    elif chess.square_file(requested_move.from_square) == chess.square_file(requested_move.to_square):
                        if abs(chess.square_rank(requested_move.from_square) - chess.square_rank(
                                requested_move.to_square)) == 2:
                            if board.piece_at(chess.square(chess.square_file(requested_move.to_square), (
                                    chess.square_rank(requested_move.from_square) + (
                            1 if chess.square_rank(requested_move.to_square) > chess.square_rank(
                                    requested_move.from_square) else -1)))) is not None:
                                new_boards.add(state)

                        else:
                            if board.piece_at(requested_move.to_square) is not None:
                                new_boards.add(state)
            else:
                new_boards.add(state)
        return new_boards
