import os
import sys
from datetime import datetime
from typing import TYPE_CHECKING
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFrame, QCheckBox, QMessageBox, QDialog, 
    QFileDialog, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QColor, QPen, QBrush, QPixmap, QKeySequence, QShortcut
import styles

def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()

if TYPE_CHECKING:
    from contestant_window import ContestantWindow


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ImagePreviewDialog(QDialog):
    """Popup window to preview the saved PNG image of the board."""
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("保存された盤面画像プレビュー")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(styles.APP_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Label to show image
        self.img_label = QLabel(self)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap(image_path)
        # Scale to fit window while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(
            QSize(680, 500), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.img_label.setPixmap(scaled_pixmap)
        
        # Path label
        path_label = QLabel(f"保存先: {image_path}", self)
        path_label.setStyleSheet("color: #38bdf8; font-weight: bold;")
        path_label.setWordWrap(True)
        
        # Close button
        close_btn = QPushButton("閉じる", self)
        close_btn.clicked.connect(self.close)
        
        layout.addWidget(self.img_label, 1)
        layout.addWidget(path_label)
        layout.addWidget(close_btn)


class ResultsDialog(QDialog):
    """Announcement dialog displaying game results, ranks, and winners."""
    def __init__(self, scores: dict[str, int], players: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎉 結果発表 🎉")
        self.setMinimumSize(450, 400)
        self.setStyleSheet(styles.APP_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Main Title
        title_label = QLabel("👑 最終結果 👑", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Outfit", 22, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #f59e0b;")
        layout.addWidget(title_label)
        
        # Rank calculation
        # players are sorted by score descending
        player_scores = []
        for p in players:
            color = p["color"]
            score = scores.get(color, 0)
            player_scores.append((score, p))
            
        player_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Determine ranks (handling ties)
        ranked_players = []
        current_rank = 1
        for idx, (score, p) in enumerate(player_scores):
            if idx > 0 and score < player_scores[idx - 1][0]:
                current_rank = idx + 1
            ranked_players.append((current_rank, score, p))
            
        # Display scores card by card
        rank_container = QFrame(self)
        rank_container.setObjectName("panel_card")
        rank_container.setStyleSheet("background-color: rgba(15, 23, 42, 0.9); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;")
        rank_layout = QVBoxLayout(rank_container)
        rank_layout.setSpacing(10)
        rank_layout.setContentsMargins(15, 15, 15, 15)
        
        for rank, score, p in ranked_players:
            p_row = QHBoxLayout()
            
            # Rank label
            rank_text = f"第 {rank} 位"
            if rank == 1:
                rank_text = "🥇 1位"
            elif rank == 2:
                rank_text = "🥈 2位"
            elif rank == 3:
                rank_text = "🥉 3位"
                
            rank_lbl = QLabel(rank_text, self)
            rank_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
            rank_lbl.setMinimumWidth(80)
            
            # Player color square
            color_sq = QLabel(self)
            color_sq.setFixedSize(16, 16)
            color_sq.setStyleSheet(f"background-color: {p['color']}; border: 1px solid white; border-radius: 4px;")
            
            # Player name & count
            name_lbl = QLabel(f"{p['name']}", self)
            name_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
            
            score_lbl = QLabel(f"{score} 枚", self)
            score_lbl.setFont(QFont("Outfit", 14, QFont.Weight.Bold))
            score_lbl.setStyleSheet("color: #38bdf8;")
            score_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            
            p_row.addWidget(rank_lbl)
            p_row.addWidget(color_sq)
            p_row.addWidget(name_lbl)
            p_row.addStretch()
            p_row.addWidget(score_lbl)
            
            rank_layout.addLayout(p_row)
            
        layout.addWidget(rank_container)
        
        # Winner announcement
        winners = [p["name"] for rank, score, p in ranked_players if rank == 1]
        winner_text = " & ".join(winners)
        winner_label = QLabel(f"🏆 勝者: {winner_text} 🏆", self)
        winner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        winner_label.setFont(QFont("Outfit", 18, QFont.Weight.Bold))
        winner_label.setStyleSheet("color: #10b981; margin-top: 10px;")
        layout.addWidget(winner_label)
        
        # OK Button
        ok_btn = QPushButton("閉じる", self)
        ok_btn.setObjectName("primary_btn")
        ok_btn.clicked.connect(self.close)
        layout.addWidget(ok_btn)


class PresenterWindow(QMainWindow):
    """The master/presenter control panel window."""
    state_updated = Signal() # Signal to trigger contestant window update

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.cells = {}
        self.player_buttons = []
        self.is_gray_restore_mode = False
        self.contestant_window: "ContestantWindow | None" = None
        self.results_announced = False
        self.autosave_error_notified = False
        
        self.setWindowTitle("出題者側操作パネル - クイズ用オセロ")
        self.setMinimumSize(760, 520)
        
        # Central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Main Layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        
        # Left Panel (Grid and Operations)
        self.left_panel = QVBoxLayout()
        self.main_layout.addLayout(self.left_panel, 6)
        
        # Header (Title & Turn)
        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("クイズ用オセロ盤面", self)
        self.title_lbl.setFont(QFont("Outfit", 18, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #38bdf8;")
        
        self.turn_lbl = QLabel(f"Turn: {self.state.turn}", self)
        self.turn_lbl.setObjectName("turn_label")
        self.turn_lbl.setFont(QFont("Outfit", 18, QFont.Weight.Bold))
        self.turn_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.turn_lbl)
        self.left_panel.addLayout(header_layout)
        
        # Othello Board Grid Container
        self.grid_container = QFrame(self)
        self.grid_container.setObjectName("othello_grid_container")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.left_panel.addWidget(self.grid_container, 7)
        
        # Left Bottom Controls
        controls_layout = QHBoxLayout()
        
        self.undo_btn = QPushButton("戻る (Ctrl+Z)", self)
        self.undo_btn.clicked.connect(self.trigger_undo)
        
        # Shortcut for Undo (Ctrl+Z)
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.trigger_undo)
        
        self.gray_restore_btn = QPushButton("灰色戻し", self)
        self.gray_restore_btn.setCheckable(True)
        self.gray_restore_btn.clicked.connect(self.toggle_gray_restore_mode)
        
        self.score_cb = QCheckBox("回答者側にもスコアを表示する", self)
        self.score_cb.setChecked(self.state.show_score_on_contestant)
        self.score_cb.stateChanged.connect(self.toggle_contestant_score)
        self.answer_always_cb = QCheckBox("常に答えを表示", self)
        self.answer_always_cb.setChecked(getattr(self.state, "show_answer_always", False))
        self.answer_always_cb.stateChanged.connect(self.toggle_answer_always)
        
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.gray_restore_btn)
        controls_layout.addWidget(self.score_cb)
        self.show_contestant_btn = QPushButton("回答者パネルを表示", self)
        self.show_contestant_btn.clicked.connect(self.show_contestant_window)
        controls_layout.addWidget(self.show_contestant_btn)
        controls_layout.addStretch()
        
        # Save actions
        self.save_json_btn = QPushButton("途中保存", self)
        self.save_json_btn.clicked.connect(self.manual_save_json)
        self.save_img_btn = QPushButton("盤面画像保存", self)
        self.save_img_btn.clicked.connect(self.save_board_image)
        self.end_game_btn = QPushButton("ゲーム終了", self)
        self.end_game_btn.clicked.connect(self.trigger_end_game_confirm)
        
        controls_layout.addWidget(self.save_json_btn)
        controls_layout.addWidget(self.save_img_btn)
        controls_layout.addWidget(self.end_game_btn)
        
        self.left_panel.addLayout(controls_layout, 1)
        
        # Right Panel (Question Info & Player Selection)
        self.right_panel = QVBoxLayout()
        self.main_layout.addLayout(self.right_panel, 4)
        
        # Scores Card
        self.score_card = QFrame(self)
        self.score_card.setObjectName("score_card")
        self.score_card_layout = QVBoxLayout(self.score_card)
        self.score_card_layout.setContentsMargins(15, 12, 15, 12)
        
        self.score_title = QLabel("【現在のスコア】", self)
        self.score_title.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.score_title.setStyleSheet("color: #38bdf8;")
        self.score_card_layout.addWidget(self.score_title)
        
        self.score_rows_container = QVBoxLayout()
        self.score_card_layout.addLayout(self.score_rows_container)
        self.right_panel.addWidget(self.score_card, 2)
        
        # Question Display Card
        self.q_card = QFrame(self)
        self.q_card.setObjectName("panel_card")
        self.q_card_layout = QVBoxLayout(self.q_card)
        self.q_card_layout.setContentsMargins(15, 15, 15, 15)
        self.q_card_layout.setSpacing(10)
        
        # Question Header (Genre, Num)
        self.q_header_lbl = QLabel("選択マス: 未選択", self)
        self.q_header_lbl.setFont(QFont("Outfit", 13, QFont.Weight.Bold))
        self.q_header_lbl.setStyleSheet("color: #60a5fa;")
        self.q_card_layout.addWidget(self.q_header_lbl)
        
        # Question Text Area (wrapped label inside scroll area)
        self.q_scroll = QScrollArea(self)
        self.q_scroll.setWidgetResizable(True)
        self.q_scroll.setStyleSheet("background: transparent; border: none;")
        self.q_scroll_content = QWidget()
        self.q_scroll_content.setStyleSheet("background: transparent;")
        self.q_scroll_layout = QVBoxLayout(self.q_scroll_content)
        self.q_scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.q_text_lbl = QLabel("盤面の灰色マスをクリックすると、クイズが出題されます。", self)
        self.q_text_lbl.setWordWrap(True)
        self.q_text_lbl.setFont(QFont("Inter", 14))
        self.q_text_lbl.setStyleSheet("color: #e2e8f0;")
        self.q_scroll_layout.addWidget(self.q_text_lbl)
        self.q_scroll.setWidget(self.q_scroll_content)
        self.q_card_layout.addWidget(self.q_scroll, 3)
        
        # Answer Text Area
        self.ans_title = QLabel("【答え】", self)
        self.ans_title.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        self.ans_title.setStyleSheet("color: #a7f3d0;")
        self.q_card_layout.addWidget(self.ans_title)
        
        self.ans_text_lbl = ClickableLabel("-", self)
        self.ans_text_lbl.setWordWrap(True)
        self.ans_text_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ans_text_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self.ans_text_lbl.setStyleSheet("color: #34d399;")
        self.ans_text_lbl.clicked.connect(self.reveal_answer)
        self.q_card_layout.addWidget(self.ans_text_lbl, 1)
        self.q_card_layout.addWidget(self.answer_always_cb)
        
        self.right_panel.addWidget(self.q_card, 5)
        
        # Player Choice Buttons Area
        self.choice_card = QFrame(self)
        self.choice_card.setStyleSheet("background-color: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 10px;")
        self.choice_layout = QVBoxLayout(self.choice_card)
        self.choice_layout.setContentsMargins(12, 12, 12, 12)
        self.choice_layout.setSpacing(8)
        
        self.choice_title = QLabel("正解した回答者を選択してください:", self)
        self.choice_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.choice_layout.addWidget(self.choice_title)
        
        # Buttons grid for players
        self.players_grid = QGridLayout()
        self.players_grid.setSpacing(8)
        self.choice_layout.addLayout(self.players_grid)
        
        # No winner row
        op_row = QHBoxLayout()
        self.no_winner_btn = QPushButton("正解者なし", self)
        self.no_winner_btn.setObjectName("no_winner_btn")
        self.no_winner_btn.clicked.connect(self.trigger_no_winner)
        
        op_row.addWidget(self.no_winner_btn, 1)
        self.choice_layout.addLayout(op_row)
        
        self.right_panel.addWidget(self.choice_card, 3)
        
        # Initialize UI Grid & Player Buttons
        self.init_board_grid()
        self.init_player_buttons()
        self.update_ui()
        
        # Apply Styles
        self.setStyleSheet(styles.APP_STYLE)

    def init_board_grid(self):
        """Creates clickable board buttons mirroring the state dimensions."""
        for r in range(self.state.rows):
            for c in range(self.state.cols):
                cell_data = self.state.board[r][c]
                btn = OthelloCellButton(cell_data["initial_id"], cell_data["initial_genre"], self)
                # Connect click handler
                btn.clicked.connect(lambda checked=False, row=r, col=c: self.on_cell_clicked(row, col))
                self.grid_layout.addWidget(btn, r, c)
                self.cells[(r, c)] = btn
                
        # Stretching
        for r in range(self.state.rows):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(self.state.cols):
            self.grid_layout.setColumnStretch(c, 1)

    def init_player_buttons(self):
        """Creates response buttons dynamically for all players."""
        # Clean grid first
        while self.players_grid.count():
            item = self.players_grid.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.player_buttons.clear()

        # Layout as 2 columns
        cols = 2
        for idx, player in enumerate(self.state.players):
            p_color = player["color"]
            p_name = player["name"]
            
            btn = QPushButton(f"{p_name}", self)
            # Give player button dynamic inline styling to match their color theme
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1e293b;
                    border: 2px solid {p_color};
                    border-radius: 6px;
                    color: {p_color};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {p_color};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked=False, color=p_color: self.trigger_winner(color))
            
            row = idx // cols
            col = idx % cols
            self.players_grid.addWidget(btn, row, col)
            self.player_buttons.append(btn)

    def update_ui(self):
        """Redraws the board, scores, questions, active state, and saves automatic backup."""
        active_cell = self.state.active_cell if self.state.active_question else None

        # 1. Update Grid Cell colors
        for (r, c), btn in self.cells.items():
            btn.set_owner(self.state.board[r][c]["color"])
            btn.set_active((r, c) == active_cell)
            btn.set_genre(self.state.board[r][c]["initial_genre"])
            
        # 2. Update Turn
        self.turn_lbl.setText(f"Turn: {self.state.turn}")
        
        # 3. Update scores display on right panel
        # Clear score rows
        while self.score_rows_container.count():
            item = self.score_rows_container.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                
        scores = self.state.get_scores()
        for p in self.state.players:
            p_color = p["color"]
            p_name = p["name"]
            count = scores.get(p_color, 0)
            
            row_frame = QFrame(self)
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 4, 0, 4)
            
            color_box = QLabel(self)
            color_box.setFixedSize(14, 14)
            color_box.setStyleSheet(f"background-color: {p_color}; border: 1px solid white; border-radius: 3px;")
            
            text_lbl = QLabel(f"{p_name}: {count}枚", self)
            text_lbl.setFont(QFont("Inter", 11, QFont.Weight.Bold))
            text_lbl.setStyleSheet("color: #e2e8f0;")
            
            row_layout.addWidget(color_box)
            row_layout.addWidget(text_lbl)
            row_layout.addStretch()
            self.score_rows_container.addWidget(row_frame)

        # 4. Checkbox synchronization
        self.score_cb.blockSignals(True)
        self.score_cb.setChecked(self.state.show_score_on_contestant)
        self.score_cb.blockSignals(False)
        self.answer_always_cb.blockSignals(True)
        self.answer_always_cb.setChecked(getattr(self.state, "show_answer_always", False))
        self.answer_always_cb.blockSignals(False)

        # 5. Question/Answer and action button states
        q = self.state.active_question
        cell = self.state.active_cell
        
        if q and cell:
            r, c = cell
            self.q_header_lbl.setText(f"出題中: {q['genre']} (マス No.{q['id']}) [行{r+1}, 列{c+1}]")
            self.q_text_lbl.setText(q["question"])
            if getattr(self.state, "show_answer_always", False) or getattr(self.state, "answer_revealed", False):
                self.ans_text_lbl.setText(q["answer"])
                self.ans_text_lbl.setToolTip("")
            else:
                self.ans_text_lbl.setText("答えを見るのはここをクリック")
                self.ans_text_lbl.setToolTip("クリックで答えを表示")
            
            # Enable winner and cancel buttons
            for btn in self.player_buttons:
                btn.setEnabled(True)
            self.no_winner_btn.setEnabled(True)
            
            self.cells[cell].set_active(True)
        else:
            self.q_header_lbl.setText("選択マス: 未選択")
            self.q_text_lbl.setText("盤面の灰色マスをクリックすると、クイズが出題されます。")
            self.ans_text_lbl.setText("-")
            self.ans_text_lbl.setToolTip("")
            
            # Disable winner and cancel buttons
            for btn in self.player_buttons:
                btn.setEnabled(False)
            self.no_winner_btn.setEnabled(False)

        # 6. Gray-restore check state
        self.gray_restore_btn.setChecked(self.is_gray_restore_mode)
        if self.is_gray_restore_mode:
            self.gray_restore_btn.setStyleSheet("background-color: #f59e0b; color: black; font-weight: bold;")
        else:
            self.gray_restore_btn.setStyleSheet("")

        # 7. Check Game Over automatically
        self.check_game_over()

        # 8. Trigger Contestant Screen update
        self.state_updated.emit()
        
        # 9. Dynamic Font Re-scaling
        self.adjust_font_sizes()
        
    def on_cell_clicked(self, r: int, c: int):
        """Click handler for cells on the board."""
        # Case A: Gray Restore Mode active
        if self.is_gray_restore_mode:
            # We want to restore a colored cell to gray
            if self.state.board[r][c]["color"] is None:
                QMessageBox.warning(self, "エラー", "このマスはすでに灰色です。色付きのマスを選択してください。")
                return
            
            success = self.state.gray_restore_cell(r, c)
            if success:
                self.is_gray_restore_mode = False
                self.autosave_json()
                self.update_ui()
            return
            
        # Case B: Standard Selection Mode.
        # If another question is already displayed, selecting a different gray cell simply switches the display.
        # The previous question is not marked used, and Turn is not incremented.
            
        if self.state.board[r][c]["color"] is not None:
            # Cannot click colored cells in normal mode
            return

        # Fetch question
        q = self.state.select_cell(r, c)
        if q:
            self.update_ui()
        else:
            # No question or no reserves left
            if not self.state.has_unused_reserves(r, c):
                QMessageBox.critical(self, "ゲーム終了", "このマスに対する予備問題がもうありません！")
                self.trigger_end_game_confirm(force=True)
            else:
                QMessageBox.warning(self, "エラー", "問題の取得に失敗しました。")

    def trigger_winner(self, color: str):
        """Marks the active question as answered correctly by player with specified color."""
        previous_turn = self.state.turn
        self.state.resolve_question_with_winner(color)
        if self.state.turn != previous_turn:
            self.autosave_json()
        self.update_ui()

    def trigger_no_winner(self):
        """Marks the active question as having no correct answer."""
        previous_turn = self.state.turn
        self.state.resolve_question_no_winner()
        if self.state.turn != previous_turn:
            self.autosave_json()
        self.update_ui()

    def trigger_undo(self):
        """Rollbacks the game state by 1 step."""
        if self.state.undo():
            self.autosave_json()
            self.update_ui()
        else:
            QMessageBox.information(self, "戻る", "これ以上戻る履歴はありません。")

    def toggle_gray_restore_mode(self):
        """Enables/Disables the special bonus gray-restore mode."""
        self.is_gray_restore_mode = self.gray_restore_btn.isChecked()
        self.update_ui()

    def toggle_contestant_score(self, checked):
        """Toggles score layout visibility on the contestant screen."""
        self.state.show_score_on_contestant = (checked == 2)
        self.autosave_json()
        self.update_ui()

    def show_contestant_window(self):
        if self.contestant_window is None:
            QMessageBox.warning(self, "回答者側パネル", "回答者側パネルが見つかりません。")
            return

        self.contestant_window.update_ui()
        self.contestant_window.show()
        self.contestant_window.raise_()
        self.contestant_window.activateWindow()

    def toggle_answer_always(self, checked):
        self.state.push_to_history()
        self.state.show_answer_always = (checked == 2)
        if self.state.show_answer_always:
            self.state.answer_revealed = True
        self.autosave_json()
        self.update_ui()

    def reveal_answer(self):
        if not self.state.active_question:
            return
        if getattr(self.state, "show_answer_always", False):
            return
        self.state.answer_revealed = True
        self.update_ui()

    def check_game_over(self):
        """Checks game over conditions and launches the results display if met."""
        # Check conditions:
        # 1. Board is full
        # 2. An unanswered cell has no more reserves
        # We handle #2 dynamically inside selection. If board is full:
        if self.state.is_board_full() and not self.results_announced:
            self.results_announced = True
            self.announce_results()

    def announce_results(self):
        """Opens results dialog."""
        scores = self.state.get_scores()
        diag = ResultsDialog(scores, self.state.players, self)
        diag.exec()

    def trigger_end_game_confirm(self, force=False):
        """Confirms ending the game manually."""
        if not force:
            reply = QMessageBox.question(
                self, "ゲーム終了確認",
                "ゲームを終了して結果発表を行いますか？\n（やり直したい場合はUndoできます）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.announce_results()

    def autosave_json(self):
        """Automatically saves state to game_backup.json next to the loaded CSV file."""
        try:
            csv_path = getattr(self.state, "csv_path", "") or getattr(self.state, "original_csv_path", "")
            backup_dir = os.path.dirname(os.path.abspath(csv_path)) if csv_path else APP_DIR
            backup_path = os.path.join(backup_dir, "game_backup.json")
            self.state.save_to_json_file(backup_path)
            self.autosave_error_notified = False
        except Exception as e:
            print(f"Autosave error: {e}", file=sys.stderr)
            if not self.autosave_error_notified:
                self.autosave_error_notified = True
                QMessageBox.warning(
                    self,
                    "オート保存エラー",
                    f"オート保存に失敗しました。\n手動保存をおすすめします。\n\n{e}",
                )

    def manual_save_json(self):
        """Prompts file save dialog to save current progress to a JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ゲームデータを保存",
            APP_DIR, "JSON Files (*.json)"
        )
        if file_path:
            try:
                self.state.save_to_json_file(file_path)
                QMessageBox.information(self, "保存完了", f"ゲームデータを保存しました:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存エラー", f"保存に失敗しました:\n{e}")

    def save_board_image(self):
        """Generates, saves, and previews a premium PNG rendering of the current board."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "盤面画像を保存", 
            os.path.join(APP_DIR, f"board_turn_{self.state.turn}.png"), "PNG Images (*.png)"
        )
        if not file_path:
            return
            
        # Draw high-quality board rendering on QPixmap
        W, H = 800, 700
        pixmap = QPixmap(W, H)
        pixmap.fill(QColor("#020617")) # Deep dark background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # 1. Background Gradient
        bg_gradient = QPen() # default pen
        # We can draw nice designs
        # Draw Turn in top-right
        painter.setPen(QColor("#38bdf8"))
        painter.setFont(QFont("Outfit", 18, QFont.Weight.Bold))
        painter.drawText(W - 200, 45, f"Turn: {self.state.turn}")
        
        # Draw App Title
        painter.setPen(QColor("#f1f5f9"))
        painter.setFont(QFont("Outfit", 20, QFont.Weight.Bold))
        painter.drawText(30, 45, "QUIZ OTHELLO BOARD")
        
        # 2. Draw Grid Layout
        grid_x, grid_y = 50, 70
        grid_w, grid_h = 700, 480
        
        cell_gap = 6
        cols = self.state.cols
        rows = self.state.rows
        
        cell_w = (grid_w - (cols - 1) * cell_gap) / cols
        cell_h = (grid_h - (rows - 1) * cell_gap) / rows
        
        for r in range(rows):
            for c in range(cols):
                cx = grid_x + c * (cell_w + cell_gap)
                cy = grid_y + r * (cell_h + cell_gap)
                
                cell_data = self.state.board[r][c]
                color_hex = cell_data["color"]
                
                # Fill brush
                if color_hex is None:
                    brush = QBrush(QColor("#1e293b"))
                    pen = QPen(QColor("#334155"), 2)
                else:
                    brush = QBrush(QColor(color_hex))
                    pen = QPen(QColor("#ffffff"), 2)
                    
                painter.setBrush(brush)
                painter.setPen(pen)
                painter.drawRoundedRect(cx, cy, cell_w, cell_h, 8, 8)
                
                # Draw ID (top-left of cell)
                painter.setPen(QColor("rgba(255, 255, 255, 0.6)"))
                painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
                painter.drawText(int(cx + 8), int(cy + 18), str(cell_data["initial_id"]))
                
                # Draw Genre (centered in cell)
                painter.setPen(QColor("#ffffff"))
                genre_text = cell_data["initial_genre"]
                length = len(genre_text)
                font_size = min(cell_w / (length * 0.75), cell_h * 0.35)
                font_size = max(min(font_size, 26), 9)
                painter.setFont(QFont("Outfit", int(font_size), QFont.Weight.Bold))
                
                # Draw text centered
                painter.drawText(
                    int(cx), int(cy + cell_h/2 - font_size/2), int(cell_w), int(cell_h/2),
                    Qt.AlignmentFlag.AlignCenter, genre_text
                )
                
        # 3. Draw Scores at bottom
        painter.setBrush(QBrush(QColor("rgba(30, 41, 59, 0.7)")))
        painter.setPen(QPen(QColor("rgba(255,255,255,0.1)"), 1))
        painter.drawRoundedRect(50, 570, 700, 90, 10, 10)
        
        # Text scores
        scores = self.state.get_scores()
        painter.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#38bdf8"))
        painter.drawText(70, 600, "【SCORE】")
        
        sx = 180
        for p in self.state.players:
            p_color = p["color"]
            p_name = p["name"]
            count = scores.get(p_color, 0)
            
            # Color block
            painter.setBrush(QBrush(QColor(p_color)))
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawRoundedRect(sx, 588, 14, 14, 3, 3)
            
            # Name and count
            painter.setPen(QColor("#f1f5f9"))
            painter.drawText(sx + 22, 601, f"{p_name}: {count}枚")
            sx += 170
            
        painter.end()
        
        # Save image
        try:
            pixmap.save(file_path, "PNG")
            
            # Show preview dialog
            preview = ImagePreviewDialog(file_path, self)
            preview.exec()
        except Exception as e:
            QMessageBox.critical(self, "画像保存エラー", f"画像の保存に失敗しました:\n{e}")

    def adjust_font_sizes(self):
        """Adjusts text element sizes in the right panel to avoid text overflows on resizing."""
        w, h = self.width(), self.height()
        
        # Grid cells (left panel)
        for (r, c), btn in self.cells.items():
            btn_w = btn.width()
            btn_h = btn.height()
            
            if btn_w <= 0 or btn_h <= 0:
                continue
                
            genre_text = btn.genre
            length = len(genre_text)
            
            genre_font_size = min(btn_w / max(length * 0.75, 1), btn_h * 0.32)
            genre_font_size = max(min(genre_font_size, 26), 6)
            btn.genre_label.setFont(QFont("Yu Gothic UI", int(genre_font_size), QFont.Weight.Bold))
            
            id_font_size = min(btn_w * 0.16, btn_h * 0.18)
            id_font_size = max(min(id_font_size, 12), 6)
            btn.id_label.setFont(QFont("Arial", int(id_font_size), QFont.Weight.Bold))

        # Scaling for right-side text boxes
        # Calculate dynamic size factors
        title_font_size = styles.get_font_size(15, w, h, 950, 700)
        q_body_font_size = styles.get_font_size(14, w, h, 950, 700)
        
        self.title_lbl.setFont(QFont("Outfit", title_font_size + 2, QFont.Weight.Bold))
        self.turn_lbl.setFont(QFont("Outfit", title_font_size + 2, QFont.Weight.Bold))
        
        self.score_title.setFont(QFont("Inter", title_font_size, QFont.Weight.Bold))
        self.fit_label_font(self.q_header_lbl, title_font_size, 7, QFont.Weight.Bold)
        self.fit_label_font(self.q_text_lbl, q_body_font_size, 7, QFont.Weight.Normal)
        self.fit_label_font(self.ans_title, title_font_size - 2, 7, QFont.Weight.Bold)
        self.fit_label_font(self.ans_text_lbl, q_body_font_size, 7, QFont.Weight.Bold)
        self.fit_label_font(self.choice_title, title_font_size, 7, QFont.Weight.Bold)

    def fit_label_font(self, label: QLabel, max_size: int, min_size: int, weight: QFont.Weight):
        text = label.text() or ""
        rect = label.contentsRect()
        width = max(rect.width(), 1)
        height = max(rect.height(), 1)
        for size in range(max(max_size, min_size), min_size - 1, -1):
            font = QFont("Yu Gothic UI", size, weight)
            metrics = QFontMetrics(font)
            bounds = metrics.boundingRect(0, 0, width, 10000, int(Qt.TextFlag.TextWordWrap), text)
            if bounds.height() <= height:
                label.setFont(font)
                return
        label.setFont(QFont("Yu Gothic UI", min_size, weight))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_font_sizes()
        
    def closeEvent(self, event):
        """Double check before exit to prevent data loss."""
        # Wait, if they close this window, we should ask
        reply = QMessageBox.question(
            self, "終了確認", "ゲームを終了してウィンドウを閉じますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.contestant_window is not None:
                self.contestant_window.allow_close = True
                self.contestant_window.close()
            event.accept()
        else:
            event.ignore()


class OthelloCellButton(QPushButton):
    """Mirroring contestant cell button for the presenter window."""
    def __init__(self, cell_id: int, genre: str, parent=None):
        super().__init__(parent)
        self.cell_id = cell_id
        self.genre = genre
        self.owner_color = None
        self.is_active = False
        self.setText("")
        self.setMinimumSize(72, 56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFlat(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)
        
        self.id_label = QLabel(str(cell_id), self)
        self.id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.id_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.id_label.setStyleSheet("background: transparent; color: rgba(255, 255, 255, 0.82); font-weight: bold; border: none; font-family: Arial;")
        
        self.genre_label = QLabel(genre, self)
        self.genre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.genre_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.genre_label.setWordWrap(True)
        self.genre_label.setStyleSheet("background: transparent; color: #ffffff; font-weight: bold; border: none; font-family: 'Yu Gothic UI', Meiryo, sans-serif;")
        
        layout.addWidget(self.id_label, 0)
        layout.addWidget(self.genre_label, 1)
        
        self.update_style()

    def set_owner(self, color: str | None):
        self.owner_color = color
        self.update_style(False)

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style(False)

    def set_genre(self, genre: str):
        self.genre = genre
        self.genre_label.setText(genre)

    def update_style(self, is_hovered: bool = False):
        if self.is_active:
            style_qss = (
                "background-color: #1e1b4b;"
                "border: 4px solid #facc15;"
                "border-radius: 8px;"
                "padding: 0px; margin: 0px;"
            )
        else:
            style_qss = styles.get_cell_style_qss(self.owner_color, is_hovered)
        self.setStyleSheet(style_qss)
        self.id_label.raise_()
        self.genre_label.raise_()

    def enterEvent(self, event):
        self.update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style(False)
        super().leaveEvent(event)
