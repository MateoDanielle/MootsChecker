import customtkinter as ctk
import threading

from mootcheck import run_mootcheck


# --------------------------------------------------
# Appearance
# --------------------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# --------------------------------------------------
# Main application
# --------------------------------------------------

class MootCheckApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("MootCheck")
        self.geometry("950x750")
        self.minsize(850, 650)

        self.results = None

        self.build_ui()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self):

        self.container = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color="transparent"
        )

        self.container.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=30
        )

        # -----------------------------
        # Header
        # -----------------------------

        self.title_label = ctk.CTkLabel(
            self.container,
            text="MOOTCHECK",
            font=ctk.CTkFont(
                size=32,
                weight="bold"
            )
        )

        self.title_label.pack(
            pady=(10, 5)
        )

        self.subtitle_label = ctk.CTkLabel(
            self.container,
            text="Instagram Mutual Checker",
            font=ctk.CTkFont(size=16)
        )

        self.subtitle_label.pack(
            pady=(0, 25)
        )

        # -----------------------------
        # Check button
        # -----------------------------

        self.check_button = ctk.CTkButton(
            self.container,
            text="CHECK MY MOOTS",
            width=220,
            height=50,
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            command=self.start_check
        )

        self.check_button.pack(
            pady=(0, 15)
        )

        # -----------------------------
        # Status
        # -----------------------------

        self.status_label = ctk.CTkLabel(
            self.container,
            text="Ready",
            font=ctk.CTkFont(size=14)
        )

        self.status_label.pack(
            pady=(0, 20)
        )

        # -----------------------------
        # Statistics
        # -----------------------------

        self.stats_frame = ctk.CTkFrame(
            self.container,
            corner_radius=15
        )

        self.stats_frame.pack(
            fill="x",
            pady=(0, 25)
        )

        for column in range(5):
            self.stats_frame.grid_columnconfigure(
                column,
                weight=1
            )

        self.followers_value = self.create_stat(
            "Followers",
            0
        )

        self.following_value = self.create_stat(
            "Following",
            1
        )

        self.mutuals_value = self.create_stat(
            "Mutuals",
            2
        )

        self.not_back_value = self.create_stat(
            "Don't Follow Back",
            3
        )

        self.you_dont_value = self.create_stat(
            "You Don't Follow",
            4
        )

        # -----------------------------
        # Results
        # -----------------------------

        self.results_frame = ctk.CTkFrame(
            self.container,
            corner_radius=15
        )

        self.results_frame.pack(
            fill="both",
            expand=True
        )

        self.results_frame.grid_columnconfigure(
            0,
            weight=1
        )

        self.results_frame.grid_columnconfigure(
            1,
            weight=1
        )

        self.results_frame.grid_rowconfigure(
            1,
            weight=1
        )

        # -----------------------------
        # Left results
        # -----------------------------

        self.left_title = ctk.CTkLabel(
            self.results_frame,
            text="Don't Follow You Back",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        )

        self.left_title.grid(
            row=0,
            column=0,
            padx=20,
            pady=(20, 10)
        )

        self.left_box = ctk.CTkTextbox(
            self.results_frame,
            font=ctk.CTkFont(size=14)
        )

        self.left_box.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(20, 10),
            pady=(0, 20)
        )

        # -----------------------------
        # Right results
        # -----------------------------

        self.right_title = ctk.CTkLabel(
            self.results_frame,
            text="You Don't Follow Back",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        )

        self.right_title.grid(
            row=0,
            column=1,
            padx=20,
            pady=(20, 10)
        )

        self.right_box = ctk.CTkTextbox(
            self.results_frame,
            font=ctk.CTkFont(size=14)
        )

        self.right_box.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(10, 20),
            pady=(0, 20)
        )

        self.set_box_text(
            self.left_box,
            "Click 'CHECK MY MOOTS' to begin."
        )

        self.set_box_text(
            self.right_box,
            "Your results will appear here."
        )

    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    def create_stat(self, title, column):

        frame = ctk.CTkFrame(
            self.stats_frame,
            fg_color="transparent"
        )

        frame.grid(
            row=0,
            column=column,
            padx=10,
            pady=18,
            sticky="nsew"
        )

        title_label = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=12)
        )

        title_label.pack()

        value_label = ctk.CTkLabel(
            frame,
            text="0",
            font=ctk.CTkFont(
                size=26,
                weight="bold"
            )
        )

        value_label.pack(
            pady=(5, 0)
        )

        return value_label

    # --------------------------------------------------
    # Textbox helper
    # --------------------------------------------------

    def set_box_text(self, box, text):

        box.configure(state="normal")

        box.delete(
            "1.0",
            "end"
        )

        box.insert(
            "1.0",
            text
        )

        box.configure(state="disabled")

    # --------------------------------------------------
    # Start check
    # --------------------------------------------------

    def start_check(self):

        self.check_button.configure(
            state="disabled",
            text="CHECKING..."
        )

        self.status_label.configure(
            text="Opening Instagram..."
        )

        self.set_box_text(
            self.left_box,
            "Collecting Instagram data..."
        )

        self.set_box_text(
            self.right_box,
            "Collecting Instagram data..."
        )

        thread = threading.Thread(
            target=self.run_check_thread,
            daemon=True
        )

        thread.start()

    # --------------------------------------------------
    # Background worker
    # --------------------------------------------------

    def run_check_thread(self):

        try:

            results = run_mootcheck()

            self.after(
                0,
                lambda: self.display_results(results)
            )

        except Exception as e:

            self.after(
                0,
                lambda error=e:
                    self.show_error(error)
            )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    def display_results(self, results):

        self.results = results

        followers = results["followers"]
        following = results["following"]
        mutuals = results["mutuals"]

        not_following_back = results[
            "not_following_back"
        ]

        followers_you_dont_follow = results[
            "followers_you_dont_follow"
        ]

        # -----------------------------
        # Statistics
        # -----------------------------

        self.followers_value.configure(
            text=str(len(followers))
        )

        self.following_value.configure(
            text=str(len(following))
        )

        self.mutuals_value.configure(
            text=str(len(mutuals))
        )

        self.not_back_value.configure(
            text=str(len(not_following_back))
        )

        self.you_dont_value.configure(
            text=str(len(followers_you_dont_follow))
        )

        # -----------------------------
        # Left list
        # -----------------------------

        if not_following_back:

            left_text = "\n".join(
                f"@{username}"
                for username in sorted(
                    not_following_back,
                    key=str.lower
                )
            )

        else:

            left_text = (
                "Everyone you follow "
                "follows you back! 🎉"
            )

        self.set_box_text(
            self.left_box,
            left_text
        )

        # -----------------------------
        # Right list
        # -----------------------------

        if followers_you_dont_follow:

            right_text = "\n".join(
                f"@{username}"
                for username in sorted(
                    followers_you_dont_follow,
                    key=str.lower
                )
            )

        else:

            right_text = (
                "You follow everyone "
                "who follows you! 🎉"
            )

        self.set_box_text(
            self.right_box,
            right_text
        )

        # -----------------------------
        # Done
        # -----------------------------

        self.status_label.configure(
            text="Done!"
        )

        self.check_button.configure(
            state="normal",
            text="CHECK MY MOOTS"
        )

    # --------------------------------------------------
    # Error handling
    # --------------------------------------------------

    def show_error(self, error):

        self.status_label.configure(
            text="Something went wrong."
        )

        self.set_box_text(
            self.left_box,
            f"Error:\n\n{error}"
        )

        self.set_box_text(
            self.right_box,
            "No results available."
        )

        self.check_button.configure(
            state="normal",
            text="TRY AGAIN"
        )


# --------------------------------------------------
# Run application
# --------------------------------------------------

if __name__ == "__main__":

    app = MootCheckApp()

    app.mainloop()