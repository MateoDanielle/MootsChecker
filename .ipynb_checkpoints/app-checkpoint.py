import customtkinter as ctk
import threading
import webbrowser
import itertools
from datetime import datetime

from mootcheck import run_mootcheck


# --------------------------------------------------
# Appearance — pastel Y2K / retro-OS window theme
# --------------------------------------------------

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

BG_MAIN = "#F3A23C"          # warm orange wallpaper
WINDOW_BORDER = "#3A2317"    # dark brown outline
CONTENT_CREAM = "#FBEFDC"    # cream window body
CONTENT_CREAM_ALT = "#F5E3C4"

TITLE_PURPLE = "#C6A8DE"
TITLE_RED = "#E85A34"

BUTTON_TAN = "#F0C987"
BUTTON_TAN_HOVER = "#E8B968"

TEXT_DARK = "#3A2317"
TEXT_MUTED = "#8A6E52"

DOT_RED = "#E8562E"
DOT_YELLOW = "#F0B93E"
DOT_TEAL = "#7FBFA6"

GREEN = "#4E9A6B"
RED = "#D9482F"
YELLOW = "#D99A2B"

ROW_ICON_COLORS = [TITLE_PURPLE, TITLE_RED, BUTTON_TAN]

FONT_TITLE = ("Comic Sans MS", 30, "bold")
FONT_SUB = ("Segoe UI", 13)
FONT_BAR_TITLE = ("Segoe UI", 13, "bold")
FONT_LABEL = ("Segoe UI", 11, "bold")
FONT_VALUE = ("Comic Sans MS", 24, "bold")
FONT_BODY = ("Segoe UI", 13)
FONT_BODY_BOLD = ("Segoe UI", 13, "bold")
FONT_BTN = ("Comic Sans MS", 15, "bold")
FONT_STATUS = ("Segoe UI", 12, "bold")
FONT_TIMESTAMP = ("Segoe UI", 11)

PROGRESS_MESSAGES = [
    "Opening Instagram...",
    "Loading saved session...",
    "Reading followers list...",
    "Scrolling followers...",
    "Reading following list...",
    "Scrolling following...",
    "Cross-referencing data...",
    "Almost done...",
]


# --------------------------------------------------
# Main application
# --------------------------------------------------

class MootCheckApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("MootCheck")
        self.geometry("1020x820")
        self.minsize(920, 700)
        self.configure(fg_color=BG_MAIN)

        self.results = None
        self.is_checking = False
        self._progress_cycle = itertools.cycle(PROGRESS_MESSAGES)
        self._progress_job = None

        self.build_ui()

    # --------------------------------------------------
    # Retro "window" helper
    # --------------------------------------------------

    def build_window(self, parent, bar_title, bar_color=TITLE_PURPLE):
        """Creates a pastel retro window frame (title bar + dots + cream body).
        Returns (outer_frame, content_frame). Caller is responsible for packing outer_frame."""

        outer = ctk.CTkFrame(
            parent,
            corner_radius=14,
            border_width=3,
            border_color=WINDOW_BORDER,
            fg_color=CONTENT_CREAM,
        )

        titlebar = ctk.CTkFrame(
            outer,
            corner_radius=0,
            fg_color=bar_color,
            height=36,
        )
        titlebar.pack(fill="x", side="top", padx=3, pady=(3, 0))
        titlebar.pack_propagate(False)

        dots = ctk.CTkFrame(titlebar, fg_color="transparent")
        dots.pack(side="left", padx=12)

        for color in (DOT_RED, DOT_YELLOW, DOT_TEAL):
            ctk.CTkLabel(
                dots, text="●", font=("Segoe UI", 13), text_color=color
            ).pack(side="left", padx=3)

        ctk.CTkLabel(
            titlebar,
            text=bar_title,
            font=FONT_BAR_TITLE,
            text_color=TEXT_DARK,
        ).pack(side="left", padx=6)

        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=18)

        return outer, content

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=34, pady=26)

        self.build_header_window()
        self.build_stats_window()
        self.build_results_window()

    # -----------------------------
    # Header window
    # -----------------------------

    def build_header_window(self):

        outer, content = self.build_window(self.container, "mootcheck.exe", TITLE_PURPLE)
        outer.pack(fill="x", pady=(0, 18))

        ctk.CTkLabel(
            content,
            text="MOOTCHECK",
            font=FONT_TITLE,
            text_color=TEXT_DARK,
        ).pack()

        ctk.CTkLabel(
            content,
            text="kingina, moots daw pero inunfriend ako",
            font=FONT_SUB,
            text_color=TEXT_MUTED,
        ).pack(pady=(2, 16))

        action_row = ctk.CTkFrame(content, fg_color="transparent")
        action_row.pack(fill="x")
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)
        action_row.grid_columnconfigure(2, weight=1)

        ctk.CTkFrame(action_row, fg_color="transparent").grid(row=0, column=0, sticky="ew")

        center = ctk.CTkFrame(action_row, fg_color="transparent")
        center.grid(row=0, column=1)

        self.check_button = ctk.CTkButton(
            center,
            text="Check My Moots",
            width=230,
            height=46,
            corner_radius=10,
            border_width=2,
            border_color=WINDOW_BORDER,
            font=FONT_BTN,
            fg_color=BUTTON_TAN,
            hover_color=BUTTON_TAN_HOVER,
            text_color=TEXT_DARK,
            command=self.start_check,
        )
        self.check_button.pack()

        status_row = ctk.CTkFrame(center, fg_color="transparent")
        status_row.pack(pady=(12, 0))

        self.status_dot = ctk.CTkLabel(
            status_row, text="●", font=("Segoe UI", 13), text_color=TEXT_MUTED
        )
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_label = ctk.CTkLabel(
            status_row, text="Ready", font=FONT_STATUS, text_color=TEXT_DARK
        )
        self.status_label.pack(side="left")

        right = ctk.CTkFrame(action_row, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")

        self.last_checked_label = ctk.CTkLabel(
            right,
            text="Last checked: never",
            font=FONT_TIMESTAMP,
            text_color=TEXT_MUTED,
        )
        self.last_checked_label.pack(anchor="e", pady=(14, 0))

    # -----------------------------
    # Stats window
    # -----------------------------

    def build_stats_window(self):

        outer, content = self.build_window(self.container, "stats.exe", TITLE_RED)
        outer.pack(fill="x", pady=(0, 18))

        stats_grid = ctk.CTkFrame(content, fg_color="transparent")
        stats_grid.pack(fill="x")

        for column in range(5):
            stats_grid.grid_columnconfigure(column, weight=1)

        self.followers_value = self.create_stat(stats_grid, "FOLLOWERS", 0)
        self.following_value = self.create_stat(stats_grid, "FOLLOWING", 1)
        self.mutuals_value = self.create_stat(stats_grid, "MUTUALS", 2)
        self.not_back_value = self.create_stat(stats_grid, "DON'T FOLLOW\nYOU BACK", 3)
        self.you_dont_value = self.create_stat(stats_grid, "YOU DON'T\nFOLLOW BACK", 4)

    def create_stat(self, parent, title, column):

        card = ctk.CTkFrame(
            parent,
            corner_radius=10,
            border_width=2,
            border_color=WINDOW_BORDER,
            fg_color=CONTENT_CREAM_ALT,
        )
        card.grid(row=0, column=column, padx=8, pady=4, sticky="nsew")

        ctk.CTkLabel(
            card,
            text=title,
            font=FONT_LABEL,
            text_color=TEXT_MUTED,
            justify="center",
        ).pack(pady=(14, 2))

        value_label = ctk.CTkLabel(
            card,
            text="—",
            font=FONT_VALUE,
            text_color=TEXT_DARK,
        )
        value_label.pack(pady=(0, 14))

        return value_label

    # -----------------------------
    # Results window
    # -----------------------------

    def build_results_window(self):

        outer, content = self.build_window(self.container, "results.exe", TITLE_PURPLE)
        outer.pack(fill="both", expand=True)

        self.tabview = ctk.CTkTabview(
            content,
            corner_radius=10,
            border_width=2,
            border_color=WINDOW_BORDER,
            fg_color=CONTENT_CREAM_ALT,
            segmented_button_fg_color=CONTENT_CREAM_ALT,
            segmented_button_selected_color=BUTTON_TAN,
            segmented_button_selected_hover_color=BUTTON_TAN_HOVER,
            segmented_button_unselected_color=CONTENT_CREAM_ALT,
            segmented_button_unselected_hover_color=CONTENT_CREAM,
            text_color=TEXT_DARK,
        )
        self.tabview.pack(fill="both", expand=True)

        self.tab_not_back = self.tabview.add("Don't Follow You Back")
        self.tab_you_dont = self.tabview.add("You Don't Follow Back")
        self.tab_mutuals = self.tabview.add("Mutuals")

        self.list_not_back = self.build_scroll_list(
            self.tab_not_back, "Click 'Check My Moots' to begin."
        )
        self.list_you_dont = self.build_scroll_list(
            self.tab_you_dont, "Click 'Check My Moots' to begin."
        )
        self.list_mutuals = self.build_scroll_list(
            self.tab_mutuals, "Click 'Check My Moots' to begin."
        )

    def build_scroll_list(self, parent, placeholder_text):

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)
        scroll.grid_columnconfigure(0, weight=1)

        self.show_placeholder(scroll, placeholder_text)

        return scroll

    # --------------------------------------------------
    # Populating lists
    # --------------------------------------------------

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    def show_placeholder(self, frame, text, emoji="🔍"):

        self.clear_frame(frame)

        wrapper = ctk.CTkFrame(frame, fg_color="transparent")
        wrapper.pack(expand=True, fill="both", pady=60)

        ctk.CTkLabel(
            wrapper, text=emoji, font=("Segoe UI", 30)
        ).pack()

        ctk.CTkLabel(
            wrapper,
            text=text,
            font=FONT_BODY,
            text_color=TEXT_MUTED,
            wraplength=500,
            justify="center",
        ).pack(pady=(10, 0))

    def populate_list(self, frame, usernames, empty_text, empty_emoji="🎉"):

        self.clear_frame(frame)

        if not usernames:
            self.show_placeholder(frame, empty_text, empty_emoji)
            return

        for index, username in enumerate(sorted(usernames, key=str.lower)):

            row = ctk.CTkFrame(
                frame,
                fg_color=CONTENT_CREAM,
                corner_radius=8,
                border_width=2,
                border_color=WINDOW_BORDER,
            )
            row.grid(row=index, column=0, sticky="ew", padx=4, pady=4)
            row.grid_columnconfigure(1, weight=1)

            icon_color = ROW_ICON_COLORS[index % len(ROW_ICON_COLORS)]

            icon = ctk.CTkLabel(
                row,
                text=username[0].upper(),
                width=30,
                height=30,
                corner_radius=6,
                fg_color=icon_color,
                text_color=TEXT_DARK,
                font=FONT_BODY_BOLD,
            )
            icon.grid(row=0, column=0, padx=(10, 10), pady=8)

            name_button = ctk.CTkButton(
                row,
                text=f"@{username}",
                anchor="w",
                corner_radius=6,
                fg_color="transparent",
                hover_color=CONTENT_CREAM_ALT,
                text_color=TEXT_DARK,
                font=FONT_BODY_BOLD,
                command=lambda u=username: self.open_profile(u),
            )
            name_button.grid(row=0, column=1, sticky="ew", pady=6)

            open_hint = ctk.CTkLabel(
                row, text="↗", font=FONT_BODY_BOLD, text_color=TEXT_MUTED
            )
            open_hint.grid(row=0, column=2, padx=(0, 12))

    def open_profile(self, username):
        webbrowser.open(f"https://www.instagram.com/{username}/")

    # --------------------------------------------------
    # Start check
    # --------------------------------------------------

    def start_check(self):

        if self.is_checking:
            return

        self.is_checking = True

        self.check_button.configure(state="disabled", text="Checking...")

        self.status_dot.configure(text_color=YELLOW)
        self.status_label.configure(text="Checking...")

        for value_label in (
            self.followers_value,
            self.following_value,
            self.mutuals_value,
            self.not_back_value,
            self.you_dont_value,
        ):
            value_label.configure(text="—")

        for frame in (self.list_not_back, self.list_you_dont, self.list_mutuals):
            self.show_placeholder(frame, "Collecting Instagram data...", "⏳")

        self._progress_cycle = itertools.cycle(PROGRESS_MESSAGES)
        self._advance_progress_message()

        thread = threading.Thread(target=self.run_check_thread, daemon=True)
        thread.start()

    def _advance_progress_message(self):

        if not self.is_checking:
            return

        self.status_label.configure(text=next(self._progress_cycle))
        self._progress_job = self.after(2500, self._advance_progress_message)

    def _stop_progress_messages(self):

        if self._progress_job is not None:
            self.after_cancel(self._progress_job)
            self._progress_job = None

    # --------------------------------------------------
    # Background worker
    # --------------------------------------------------

    def run_check_thread(self):

        try:
            results = run_mootcheck()
            self.after(0, lambda: self.display_results(results))

        except Exception as e:
            self.after(0, lambda error=e: self.show_error(error))

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    def display_results(self, results):

        self.is_checking = False
        self._stop_progress_messages()

        self.results = results

        followers = results["followers"]
        following = results["following"]
        mutuals = results["mutuals"]
        not_following_back = results["not_following_back"]
        followers_you_dont_follow = results["followers_you_dont_follow"]

        self.followers_value.configure(text=str(len(followers)))
        self.following_value.configure(text=str(len(following)))
        self.mutuals_value.configure(text=str(len(mutuals)))
        self.not_back_value.configure(text=str(len(not_following_back)))
        self.you_dont_value.configure(text=str(len(followers_you_dont_follow)))

        self.populate_list(
            self.list_not_back,
            not_following_back,
            "Everyone you follow follows you back!",
        )
        self.populate_list(
            self.list_you_dont,
            followers_you_dont_follow,
            "You follow everyone who follows you!",
        )
        self.populate_list(
            self.list_mutuals,
            mutuals,
            "No mutuals found yet.",
        )

        self.status_dot.configure(text_color=GREEN)
        self.status_label.configure(text="Complete")

        self.last_checked_label.configure(
            text=f"Last checked: {datetime.now().strftime('%b %d, %Y at %I:%M %p')}"
        )

        self.check_button.configure(state="normal", text="Check My Moots")

    # --------------------------------------------------
    # Error handling
    # --------------------------------------------------

    def show_error(self, error):

        self.is_checking = False
        self._stop_progress_messages()

        self.status_dot.configure(text_color=RED)
        self.status_label.configure(text="Something went wrong")

        for frame in (self.list_not_back, self.list_you_dont, self.list_mutuals):
            self.show_placeholder(frame, f"Error:\n{error}", "⚠️")

        self.check_button.configure(state="normal", text="Try Again")


# --------------------------------------------------
# Run application
# --------------------------------------------------

if __name__ == "__main__":

    app = MootCheckApp()
    app.mainloop()