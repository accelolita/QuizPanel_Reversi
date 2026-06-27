import os
import unittest
from csv_handler import CSVHandler, CSVHandlerError
from game_state import GameState

class TestQuizOthello(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        # Create a small dummy CSV file for testing
        self.csv_path = os.path.join(self.test_dir, "test_quiz.csv")
        self.rows = 4
        self.cols = 4 # 16 questions needed
        
        # 20 questions total.
        # Make some different genres to test reserve logic.
        # ID 1 (row 0, col 0) will be "アニメ"
        # Reserve IDs (17-20): 17 is "スポーツ", 18 is "アニメ".
        self.dummy_questions = []
        for i in range(1, 21):
            if i == 17:
                genre = "スポーツ"
            elif i == 18:
                genre = "アニメ"
            else:
                genre = "アニメ"
            self.dummy_questions.append((genre, f"問題{i}", f"答え{i}"))
        
        import csv
        with open(self.csv_path, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["ジャンル", "問題文", "答え"])
            for row in self.dummy_questions:
                writer.writerow(row)
                
        self.players = [
            {"name": "Player1", "color": "#ff0000"},
            {"name": "Player2", "color": "#00ff00"}
        ]

    def tearDown(self):
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        # Clean up shuffled tests if any in test_dir
        for f in os.listdir(self.test_dir):
            if "test_quiz_shuffled_" in f:
                try:
                    os.remove(os.path.join(self.test_dir, f))
                except:
                    pass

    def test_csv_loading_and_validation(self):
        # Test valid CSV loading without shuffle
        questions, final_path = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "シャッフルなし"
        )
        self.assertEqual(len(questions), 20)
        self.assertEqual(final_path, self.csv_path)
        self.assertEqual(questions[0]["id"], 1)
        self.assertEqual(questions[0]["genre"], "アニメ")
        self.assertEqual(questions[0]["question"], "問題1")
        self.assertEqual(questions[0]["answer"], "答え1")

        # Test validation failure for small count
        with self.assertRaises(CSVHandlerError):
            # Needs 36 questions (6x6), but only has 20
            CSVHandler.load_and_process_csv(
                self.csv_path, 6, 6, "シャッフルなし"
            )

    def test_csv_shuffle_saving(self):
        # Test shuffle all
        questions, final_path = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "全体シャッフル"
        )
        self.assertNotEqual(final_path, self.csv_path)
        self.assertTrue(os.path.exists(final_path))
        os.remove(final_path)

    def test_game_state_flow_and_othello(self):
        questions, _ = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "シャッフルなし"
        )
        state = GameState(
            rows=self.rows,
            cols=self.cols,
            csv_path=self.csv_path,
            original_csv_path=self.csv_path,
            shuffle_type="シャッフルなし",
            questions=questions,
            players=self.players
        )
        
        p1 = self.players[0]["color"] # Red
        p2 = self.players[1]["color"] # Green
        
        # Select cell (0, 0)
        q = state.select_cell(0, 0)
        self.assertIsNotNone(q)
        self.assertEqual(q["id"], 1) # First cell, initial ID is 1
        
        # Answer by p1
        state.resolve_question_with_winner(p1)
        self.assertEqual(state.board[0][0]["color"], p1)
        self.assertEqual(state.turn, 1)
        self.assertIn(1, state.used_questions_ids)
        
        # Select cell (0, 1), answer by p2
        state.select_cell(0, 1)
        state.resolve_question_with_winner(p2)
        self.assertEqual(state.board[0][1]["color"], p2)
        
        # Select cell (0, 2), answer by p1. This should sandwich (0, 1) and flip it to p1!
        state.select_cell(0, 2)
        state.resolve_question_with_winner(p1)
        self.assertEqual(state.board[0][2]["color"], p1)
        self.assertEqual(state.board[0][1]["color"], p1) # Flipped!
        
        # Test score counting
        scores = state.get_scores()
        self.assertEqual(scores[p1], 3)
        self.assertEqual(scores[p2], 0)

        # Test Undo
        self.assertTrue(state.undo())
        # Should rollback to before cell (0, 2) was answered. (0, 1) should be p2, and (0, 2) should be None.
        self.assertEqual(state.board[0][2]["color"], None)
        self.assertEqual(state.board[0][1]["color"], p2)
        self.assertEqual(state.turn, 2)
        
        # Test gray restore
        state.gray_restore_cell(0, 1)
        self.assertEqual(state.board[0][1]["color"], None)
        # Check that undoing gray restore works
        state.undo()
        self.assertEqual(state.board[0][1]["color"], p2)

    def test_reserve_question_rules(self):
        questions, _ = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "シャッフルなし"
        )
        state = GameState(
            rows=self.rows,
            cols=self.cols,
            csv_path=self.csv_path,
            original_csv_path=self.csv_path,
            shuffle_type="シャッフルなし",
            questions=questions,
            players=self.players
        )
        p1 = self.players[0]["color"]
        
        # Click (0, 0)
        state.select_cell(0, 0)
        state.resolve_question_with_winner(p1) # ID 1 is now used
        
        # Restore (0, 0) to gray
        state.gray_restore_cell(0, 0)
        self.assertEqual(state.board[0][0]["color"], None)
        # Check that the cell's genre has updated to the next reserve genre ("スポーツ")
        self.assertEqual(state.board[0][0]["initial_genre"], "スポーツ")
        self.assertEqual(state.board[0][0]["initial_id"], 17)
        
        # Click (0, 0) again. It should fetch a reserve question
        q = state.select_cell(0, 0)
        self.assertIsNotNone(q)
        self.assertEqual(q["id"], 17)
        self.assertEqual(q["genre"], "スポーツ")

    def test_resolve_no_winner_genre_update(self):
        questions, _ = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "シャッフルなし"
        )
        state = GameState(
            rows=self.rows,
            cols=self.cols,
            csv_path=self.csv_path,
            original_csv_path=self.csv_path,
            shuffle_type="シャッフルなし",
            questions=questions,
            players=self.players
        )
        
        # Click (0, 0) which initially has genre "アニメ" (ID 1)
        self.assertEqual(state.board[0][0]["initial_genre"], "アニメ")
        state.select_cell(0, 0)
        
        # Resolve with no winner
        state.resolve_question_no_winner()
        
        # Check that the cell's genre and id are updated on no winner resolution
        self.assertEqual(state.board[0][0]["initial_genre"], "スポーツ")
        self.assertEqual(state.board[0][0]["initial_id"], 17)

    def test_no_winner_consecutive_duplicates(self):
        questions, _ = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "シャッフルなし"
        )
        state = GameState(
            rows=self.rows,
            cols=self.cols,
            csv_path=self.csv_path,
            original_csv_path=self.csv_path,
            shuffle_type="シャッフルなし",
            questions=questions,
            players=self.players
        )
        
        # 1. Click cell (0, 0) and resolve with no winner
        state.select_cell(0, 0)
        state.resolve_question_no_winner()
        self.assertEqual(state.board[0][0]["initial_id"], 17) # First reserve
        
        # 2. Click cell (0, 1) and resolve with no winner
        state.select_cell(0, 1)
        state.resolve_question_no_winner()
        
        # Cell (0, 1) should get the next reserve (ID 18), NOT ID 17
        self.assertEqual(state.board[0][1]["initial_id"], 18)
        self.assertNotEqual(state.board[0][0]["initial_id"], state.board[0][1]["initial_id"])

    def test_swap_conditions_trigger_only_once(self):
        questions, _ = CSVHandler.load_and_process_csv(
            self.csv_path, self.rows, self.cols, "シャッフルなし"
        )
        state = GameState(
            rows=self.rows,
            cols=self.cols,
            csv_path=self.csv_path,
            original_csv_path=self.csv_path,
            shuffle_type="シャッフルなし",
            questions=questions,
            players=self.players
        )
        p1 = self.players[0]["color"]
        p2 = self.players[1]["color"]
        
        # 16マス中、8マス埋める（50%）
        # p1を5マス、p2を3マスにして、p2が最少マスの状態を作る
        for r in range(2):
            for c in range(4):
                state.board[r][c]["color"] = p1
        state.board[1][3]["color"] = p2
        state.board[1][2]["color"] = p2
        state.board[1][1]["color"] = p2
        
        # 現在のスコア: p1 = 5, p2 = 3 (最少マスは p2)
        # 最少マスの p2 が正解した時の swap condition をチェック
        # ratio = 8/16 = 50%
        self.assertEqual(state.check_swap_condition(p2), "half")
        
        # p1が正解した場合は最少マスではないので None になるはず
        self.assertIsNone(state.check_swap_condition(p1))
        
        # 実際に swap を行い、半分突破枠のフラグを True に更新
        state.swap_half_used = True
        
        # フラグが更新されたので、再度同じ条件でも swap condition は None になるはず
        self.assertIsNone(state.check_swap_condition(p2))
        
        # マスを 14マス埋める (14/16 = 87.5% = 7/8以上)
        # p1を9マス、p2を5マスにする（計14マス）
        for r in range(3):
            for c in range(4):
                state.board[r][c]["color"] = p1
        state.board[3][0]["color"] = p1
        state.board[3][1]["color"] = p1
        
        state.board[2][3]["color"] = p2
        state.board[2][2]["color"] = p2
        state.board[2][1]["color"] = p2
        state.board[2][0]["color"] = p2
        state.board[1][3]["color"] = p2
        # ratio = 14/16 = 87.5%
        # 最少マスの p2 が正解した時の swap condition をチェック
        self.assertEqual(state.check_swap_condition(p2), "seven_eighths")
        
        # 実際に swap を行い、7/8突破枠のフラグを True に更新
        state.swap_seven_eighths_used = True
        
        # 再度チェックしたら None になるはず
        self.assertIsNone(state.check_swap_condition(p2))

if __name__ == "__main__":
    unittest.main()
