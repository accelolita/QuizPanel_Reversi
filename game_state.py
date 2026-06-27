import copy
import json
import os

class GameState:
    def __init__(self, rows: int, cols: int, csv_path: str, original_csv_path: str, shuffle_type: str, questions: list[dict], players: list[dict]):
        self.rows = rows
        self.cols = cols
        self.csv_path = csv_path
        self.original_csv_path = original_csv_path
        self.shuffle_type = shuffle_type
        self.questions = questions  # All loaded questions in order (1-indexed based on dict 'id')
        self.players = players      # list of {'name': str, 'color': str}

        # Active question state
        self.active_question = None  # Current question dict or None
        self.active_cell = None      # Tuple (r, c) or None
        
        # Turn count
        self.turn = 0
        
        # Show score on contestant screen
        self.show_score_on_contestant = False
        self.show_answer_always = False
        self.answer_revealed = False
        
        # Track used questions (contains question IDs, 1-indexed)
        self.used_questions_ids = set()

        # Board state
        # 2D list of cells. A cell is a dict with keys: 'color', 'initial_genre', 'initial_id'
        self.board = []
        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                idx = r * self.cols + c
                q = self.questions[idx]
                row_cells.append({
                    "color": None,           # None means gray (unowned)
                    "initial_genre": q["genre"],
                    "initial_id": q["id"]
                })
            self.board.append(row_cells)

        # Internal Undo Stack
        self.history_stack = []

    def get_question_by_id(self, q_id: int) -> dict | None:
        """Returns the question with the given ID (1-indexed)."""
        # Since they are in order in self.questions, index is q_id - 1
        if 0 < q_id <= len(self.questions):
            return self.questions[q_id - 1]
        return None

    def push_to_history(self):
        """Pushes a deep copy of the current state to the undo history stack."""
        self.history_stack.append(self.save_to_dict())

    def undo(self) -> bool:
        """Restores the state from the last history snapshot. Returns True if successful."""
        if not self.history_stack:
            return False
        prev_state = self.history_stack.pop()
        self.load_from_dict(prev_state)
        return True

    def get_scores(self) -> dict[str, int]:
        """Calculates current cell counts for each player color."""
        scores = {p["color"]: 0 for p in self.players}
        for r in range(self.rows):
            for c in range(self.cols):
                color = self.board[r][c]["color"]
                if color in scores:
                    scores[color] += 1
        return scores

    def select_cell(self, r: int, c: int) -> dict | None:
        """
        Processes a click on cell (r, c) to fetch the appropriate question.
        Returns the question dict to display, or None if no question is available or cell is colored.
        """
        # Colored cells cannot be selected normally
        if self.board[r][c]["color"] is not None:
            return None

        self.active_cell = (r, c)
        self.answer_revealed = False
        
        # Determine which question to load
        initial_id = self.board[r][c]["initial_id"]
        
        # If the cell's initial question is unused, use it
        if initial_id not in self.used_questions_ids:
            self.active_question = self.get_question_by_id(initial_id)
            return self.active_question
        
        # Otherwise, search for a reserve question
        reserve_q = self._find_reserve_question()
        if reserve_q:
            self.active_question = reserve_q
            return self.active_question
        
        # If no reserve question, we return None (main window will handle game over)
        self.active_question = None
        self.answer_revealed = False
        return None

    def _find_reserve_question(self) -> dict | None:
        """
        Finds an unused reserve question (ID > rows * cols).
        Rules:
        1. First unused reserve question of any genre
        """
        initial_count = self.rows * self.cols
        reserve_questions = self.questions[initial_count:]
        
        # Rule: Any genre
        for q in reserve_questions:
            if q["id"] not in self.used_questions_ids:
                return q
                
        return None

    def resolve_question_with_winner(self, winner_color: str):
        """Marks active question as solved by a winner, flips cells, and increments turn."""
        if not self.active_question or not self.active_cell:
            return

        self.push_to_history()
        
        r, c = self.active_cell
        self.board[r][c]["color"] = winner_color
        self.used_questions_ids.add(self.active_question["id"])
        
        # Perform Othello flips
        self._flip_othello(r, c, winner_color)
        
        self.turn += 1
        self.active_question = None
        self.active_cell = None
        self.answer_revealed = False

    def resolve_question_no_winner(self):
        """Marks active question as solved with no winner (cell remains gray), and increments turn."""
        if not self.active_question or not self.active_cell:
            return

        self.push_to_history()
        
        # Cell stays gray (color = None)
        self.used_questions_ids.add(self.active_question["id"])
        
        # Update cell details to the next reserve question if available
        r, c = self.active_cell
        next_q = self._find_reserve_question()
        if next_q:
            self.board[r][c]["initial_genre"] = next_q["genre"]
            self.board[r][c]["initial_id"] = next_q["id"]
        
        self.turn += 1
        self.active_question = None
        self.active_cell = None
        self.answer_revealed = False

    def gray_restore_cell(self, r: int, c: int) -> bool:
        """
        Manually restores a colored cell to gray.
        Does not change Turn, does not trigger Othello flips.
        Returns True if successful.
        """
        if self.board[r][c]["color"] is None:
            return False # Already gray
            
        self.push_to_history()
        
        self.board[r][c]["color"] = None
        # We do NOT remove the question from used_questions_ids. It stays used.
        # Next time they click this cell, it will ask a reserve question.
        # Update cell details to the next reserve question if available
        next_q = self._find_reserve_question()
        if next_q:
            self.board[r][c]["initial_genre"] = next_q["genre"]
            self.board[r][c]["initial_id"] = next_q["id"]
        return True

    def _flip_othello(self, r: int, c: int, player_color: str):
        """Standard Othello 8-direction flipping logic."""
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        cells_to_flip = []
        
        for dr, dc in directions:
            current_flips = []
            curr_r, curr_c = r + dr, c + dc
            
            while 0 <= curr_r < self.rows and 0 <= curr_c < self.cols:
                cell_color = self.board[curr_r][curr_c]["color"]
                
                if cell_color is None:
                    # Hit a gray cell - abort this direction
                    break
                elif cell_color == player_color:
                    # Hit our own color - we can flip everything collected in this direction
                    cells_to_flip.extend(current_flips)
                    break
                else:
                    # Hit an opponent color - collect and continue
                    current_flips.append((curr_r, curr_c))
                    
                curr_r += dr
                curr_c += dc
                
        # Apply flips
        for flip_r, flip_c in cells_to_flip:
            self.board[flip_r][flip_c]["color"] = player_color

    def is_board_full(self) -> bool:
        """Returns True if all cells on the board have been colored."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c]["color"] is None:
                    return False
        return True

    def has_unused_reserves(self, r: int, c: int) -> bool:
        """Checks if a reserve question is available for the given cell."""
        return self._find_reserve_question() is not None

    def save_to_dict(self) -> dict:
        """Serializes the game state to a dictionary (JSON-compatible)."""
        return {
            "rows": self.rows,
            "cols": self.cols,
            "csv_path": self.csv_path,
            "original_csv_path": self.original_csv_path,
            "shuffle_type": self.shuffle_type,
            "questions": self.questions,
            "players": self.players,
            "turn": self.turn,
            "show_score_on_contestant": self.show_score_on_contestant,
            "show_answer_always": self.show_answer_always,
            "answer_revealed": self.answer_revealed,
            "used_questions_ids": list(self.used_questions_ids),
            "board": [
                [
                    {
                        "color": cell["color"],
                        "initial_genre": cell["initial_genre"],
                        "initial_id": cell["initial_id"]
                    }
                    for cell in row
                ]
                for row in self.board
            ],
            "active_question": self.active_question,
            "active_cell": self.active_cell
        }

    def load_from_dict(self, data: dict):
        """Restores the game state from a dictionary."""
        self.rows = data["rows"]
        self.cols = data["cols"]
        self.csv_path = data["csv_path"]
        self.original_csv_path = data["original_csv_path"]
        self.shuffle_type = data["shuffle_type"]
        self.questions = data["questions"]
        self.players = data["players"]
        self.turn = data["turn"]
        self.show_score_on_contestant = data["show_score_on_contestant"]
        self.show_answer_always = data.get("show_answer_always", False)
        self.answer_revealed = data.get("answer_revealed", False)
        self.used_questions_ids = set(data["used_questions_ids"])
        
        self.board = []
        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                cell_data = data["board"][r][c]
                row_cells.append({
                    "color": cell_data["color"],
                    "initial_genre": cell_data["initial_genre"],
                    "initial_id": cell_data["initial_id"]
                })
            self.board.append(row_cells)
            
        self.active_question = data["active_question"]
        self.active_cell = tuple(data["active_cell"]) if data["active_cell"] else None

    def save_to_json_file(self, file_path: str):
        """Saves the serialized game state to a JSON file."""
        state_dict = self.save_to_dict()
        # Also store the history stack so we can resume undo history if desired
        state_dict["history_stack"] = self.history_stack
        tmp_path = f"{file_path}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)

    @classmethod
    def load_from_json_file(cls, file_path: str) -> "GameState":
        """Loads and returns a GameState instance from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Instantiate with skeleton variables
        instance = cls(
            rows=data["rows"],
            cols=data["cols"],
            csv_path=data["csv_path"],
            original_csv_path=data["original_csv_path"],
            shuffle_type=data["shuffle_type"],
            questions=data["questions"],
            players=data["players"]
        )
        instance.load_from_dict(data)
        if "history_stack" in data:
            instance.history_stack = data["history_stack"]
        return instance
