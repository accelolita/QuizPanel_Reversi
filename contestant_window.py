import sys
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
from PySide6.QtGui import QFont, QFontMetrics
import styles

class OthelloCellButton(QPushButton):
    """Custom button for Othello grid cell with custom text elements and hover events."""
    def __init__(self, cell_id: int, genre: str, parent=None):
        super().__init__(parent)
        self.cell_id = cell_id
        self.genre = genre
        self.owner_color = None
        self.is_active = False
        self.setObjectName("othello_cell_button")
        self.setText("")
        self.setMinimumSize(72, 56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Disable default styling to allow custom backgrounds via inline CSS
        self.setFlat(True)
        
        # ID label in the corner (top-left as per specifications) - absolute layout
        self.id_label = QLabel(str(cell_id), self)
        self.id_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.id_label.setStyleSheet("background: transparent; color: rgba(255, 255, 255, 0.82); font-weight: bold; border: none; font-family: Arial;")
        
        # Genre label in the center - absolute layout
        self.genre_label = QLabel(genre, self)
        self.genre_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.genre_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.genre_label.setWordWrap(True)
        self.genre_label.setStyleSheet("background: transparent; color: #ffffff; font-weight: bold; border: none; font-family: 'Yu Gothic UI', Meiryo, sans-serif;")
        
        self.update_style()

    def set_owner(self, color: str | None):
        """Sets the owner player color of this cell."""
        self.owner_color = color
        self.update_style(False)

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style(False)

    def set_genre(self, genre: str):
        self.genre = genre
        self.genre_label.setText(genre)

    def update_style(self, is_hovered: bool = False):
        """Updates the style of the cell button."""
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position child labels absolute relative to the button width/height
        self.id_label.setGeometry(6, 4, self.width() - 12, 16)
        self.genre_label.setGeometry(6, 18, self.width() - 12, self.height() - 22)
        self.id_label.raise_()
        self.genre_label.raise_()

    def enterEvent(self, event):
        self.update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style(False)
        super().leaveEvent(event)


class ContestantWindow(QMainWindow):
    """Window showing the Othello grid and optionally the scores for the contestants/audience."""
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.allow_close = False
        self.cells = {} # Dict mapping (r, c) to OthelloCellButton
        self.score_labels = [] # List of score labels for updating
        self.setWindowTitle("回答者側パネル - クイズ用オセロ")
        self.setMinimumSize(600, 500)
        
        # Set central widget and layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.title_lbl = QLabel("クイズ用オセロ盤面", self)
        self.title_lbl.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.turn_lbl = QLabel(f"Turn: {self.state.turn}", self)
        self.turn_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.turn_lbl.setStyleSheet("color: #38bdf8; font-weight: bold;")
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.turn_lbl)
        self.main_layout.addLayout(header_layout)
        
        # Grid container frame
        self.grid_container = QFrame(self)
        self.grid_container.setObjectName("othello_grid_container")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.addWidget(self.grid_container, 8)
        
        # Score card frame (collapsible/toggleable)
        self.score_card = QFrame(self)
        self.score_card.setObjectName("score_card")
        self.score_layout = QHBoxLayout(self.score_card)
        self.score_layout.setContentsMargins(15, 10, 15, 10)
        self.score_layout.setSpacing(20)
        self.main_layout.addWidget(self.score_card, 1)
        
        # Initialize UI elements
        self.init_grid()
        self.init_scores()
        self.update_ui()
        
        # Apply global style
        self.setStyleSheet(styles.APP_STYLE)

    def init_grid(self):
        """Creates the grid cell buttons based on state dimensions."""
        for r in range(self.state.rows):
            for c in range(self.state.cols):
                cell_data = self.state.board[r][c]
                btn = OthelloCellButton(cell_data["initial_id"], cell_data["initial_genre"], self)
                # Note: We do not bind click event on contestant screen; clicks happen on presenter screen.
                # However, to be interactive, we can enable it or just let presenter trigger actions.
                # In standard usage, contestant screen is view-only, but let's make it fully responsive.
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Presenter controls everything
                
                self.grid_layout.addWidget(btn, r, c)
                self.cells[(r, c)] = btn
                
        # Make grid columns and rows stretch equally
        for r in range(self.state.rows):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(self.state.cols):
            self.grid_layout.setColumnStretch(c, 1)

    def init_scores(self):
        """Creates score indicator labels for each player."""
        # Clear old items if any
        while self.score_layout.count():
            item = self.score_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.score_labels.clear()

        # Add headers or container
        title_lbl = QLabel("【スコア】", self)
        title_lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
        self.score_layout.addWidget(title_lbl)
        self.score_labels.append(title_lbl)
        
        for player in self.state.players:
            p_color = player["color"]
            p_name = player["name"]
            
            # Sub-container for player score
            p_frame = QFrame(self)
            p_frame.setStyleSheet("background: transparent;")
            p_layout = QHBoxLayout(p_frame)
            p_layout.setContentsMargins(0, 0, 0, 0)
            p_layout.setSpacing(6)
            
            # Color block
            color_block = QLabel(self)
            color_block.setFixedSize(16, 16)
            color_block.setStyleSheet(f"background-color: {p_color}; border: 1px solid white; border-radius: 4px;")
            
            # Score label
            score_lbl = QLabel(f"{p_name}: 0枚", self)
            score_lbl.setStyleSheet(f"color: #f1f5f9; font-weight: bold;")
            
            p_layout.addWidget(color_block)
            p_layout.addWidget(score_lbl)
            
            self.score_layout.addWidget(p_frame)
            # Store reference to the label and the block for updating/resizing
            self.score_labels.append((score_lbl, player))
            
        self.score_layout.addStretch()

    def update_ui(self):
        """Updates board colors and scores from the current state."""
        # 1. Update Grid Colors
        active_cell = self.state.active_cell if self.state.active_question else None
        for (r, c), btn in self.cells.items():
            btn.set_owner(self.state.board[r][c]["color"])
            btn.set_active((r, c) == active_cell)
            btn.set_genre(self.state.board[r][c]["initial_genre"])
            
        # 2. Toggle Score card visibility
        self.score_card.setVisible(self.state.show_score_on_contestant)
        self.turn_lbl.setText(f"Turn: {self.state.turn}")
        
        # 3. Update Scores
        scores = self.state.get_scores()
        for item in self.score_labels:
            if isinstance(item, tuple):
                label, player = item
                color = player["color"]
                name = player["name"]
                count = scores.get(color, 0)
                label.setText(f"{name}: {count}枚")
                
        # Re-adjust fonts after state changes
        self.adjust_font_sizes()

    def adjust_font_sizes(self):
        """Dynamically updates font sizes based on cell button dimensions and text length."""
        w, h = self.width(), self.height()
        
        # Adjust grid cells
        for (r, c), btn in self.cells.items():
            btn_w = btn.width()
            btn_h = btn.height()
            
            if btn_w <= 0 or btn_h <= 0:
                continue
                
            genre_text = btn.genre
            length = len(genre_text)
            
            label_x = 6
            label_y = max(18, int(btn_h * 0.27))
            label_w = max(1, btn_w - 12)
            label_h = max(1, btn_h - label_y - 8)

            base_size = min(btn_w / max(length * 0.82, 1), btn_h * 0.30)
            max_size = int(max(min(base_size, 30), 6))
            genre_font = QFont("Yu Gothic UI", 6, QFont.Weight.Bold)
            flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
            for size in range(max_size, 5, -1):
                candidate = QFont("Yu Gothic UI", size, QFont.Weight.Bold)
                metrics = QFontMetrics(candidate)
                bounds = metrics.boundingRect(0, 0, label_w, label_h, flags, genre_text)
                if bounds.width() <= label_w and bounds.height() <= label_h:
                    genre_font = candidate
                    break

            btn.genre_label.setFont(genre_font)
            btn.genre_label.setGeometry(label_x, label_y, label_w, label_h)
            
            # ID Font Size
            id_font_size = min(btn_w * 0.16, btn_h * 0.18)
            id_font_size = max(min(id_font_size, 13), 6)
            btn.id_label.setFont(QFont("Arial", int(id_font_size), QFont.Weight.Bold))
            btn.id_label.setGeometry(6, 4, max(1, btn_w - 12), max(14, int(btn_h * 0.22)))
            btn.id_label.raise_()
            btn.genre_label.raise_()

        # Adjust score text
        score_base = styles.get_font_size(12, w, h, 800, 600)
        header_size = styles.get_font_size(18, w, h, 800, 600)
        self.title_lbl.setFont(QFont("Yu Gothic UI", max(header_size, 8), QFont.Weight.Bold))
        self.turn_lbl.setFont(QFont("Arial", max(header_size, 8), QFont.Weight.Bold))
        for item in self.score_labels:
            if isinstance(item, tuple):
                label, _ = item
                label.setFont(QFont("Inter", score_base, QFont.Weight.Bold))
            elif isinstance(item, QLabel):
                item.setFont(QFont("Inter", score_base, QFont.Weight.Bold))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_font_sizes()

    def closeEvent(self, event):
        if self.allow_close:
            event.accept()
            return

        self.hide()
        event.ignore()
