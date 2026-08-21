"""
MootCheck — Windows XP "Luna" themed edition.

This is a full visual rebuild. customtkinter can't fake real XP window
chrome (gradient title bars, beveled 3D buttons, draggable dialog windows),
so this version drops down to plain Tkinter + Pillow and hand-draws the
XP look: gradient title bars, red/blue title-bar buttons, classic
"Windows XP" info dialogs, a segmented marquee progress bar, and a
cascade of draggable result windows over the Bliss wallpaper.

Requires: Pillow  (pip install pillow --break-system-packages)

Drop mootcheck.py (with run_mootcheck()) next to this file, and put the
wallpaper image at assets/bliss_wallpaper.png (or change WALLPAPER_PATH
below).
"""

import itertools
import os
import threading
import webbrowser
from datetime import datetime

import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageTk

try:
    from mootcheck import run_mootcheck
except ImportError:
    # Fallback demo data so this file can be run/previewed on its own
    # even if mootcheck.py isn't next to it yet. Safe to leave in place;
    # it only triggers if the real import fails.
    def run_mootcheck():
        import time
        import random

        time.sleep(3)
        rnd = random.Random(7)
        followers = {f"follower_{i}" for i in range(1, 140)}
        following = {f"follower_{i}" for i in range(1, 100)} | {
            f"crush_{i}" for i in range(1, 15)
        }
        mutuals = followers & following
        not_following_back = following - followers
        followers_you_dont_follow = followers - following
        return {
            "followers": followers,
            "following": following,
            "mutuals": mutuals,
            "not_following_back": not_following_back,
            "followers_you_dont_follow": followers_you_dont_follow,
        }


# ============================================================
# Paths / geometry
# ============================================================

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
WALLPAPER_PATH = os.path.join(ASSETS_DIR, "bliss_wallpaper.png")

APP_W, APP_H = 1024, 640

# ============================================================
# Colors — Windows XP "Luna" blue theme
# ============================================================

TITLEBAR_TOP = (0, 88, 230)
TITLEBAR_MID = (150, 200, 255)
TITLEBAR_BOTTOM = (0, 40, 170)
TITLEBAR_BORDER = "#0A246A"

DIALOG_BG = "#ECE9D8"          # classic XP dialog beige
WINDOW_BODY_BG = "#FFFFFF"     # list windows are white like a real content pane

CLOSE_FILL = "#E8433A"
CLOSE_OUTLINE = "#B22A22"
MINMAX_FILL = "#3D95FF"
MINMAX_OUTLINE = "#1E5FBD"

PROGRESS_BLOCK = "#1E9C3E"
PROGRESS_BLOCK_EDGE = "#0F5220"
PROGRESS_BG = "#FFFFFF"
PROGRESS_BORDER = "#7A96DF"

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


# ============================================================
# Font selection — pick the closest installed fonts
# ============================================================

def _first_available(candidates, fallback):
    try:
        families = set(tkfont.families())
    except Exception:
        return fallback
    for name in candidates:
        if name in families:
            return name
    return fallback


UI_FONT_FAMILY = None      # resolved after a root window exists
LOGO_FONT_FAMILY = None


def resolve_fonts():
    global UI_FONT_FAMILY, LOGO_FONT_FAMILY
    UI_FONT_FAMILY = _first_available(
        ["Tahoma", "Segoe UI", "MS Sans Serif", "Arial"], "Arial"
    )
    LOGO_FONT_FAMILY = _first_available(
        ["Vivaldi", "Segoe Script", "Brush Script MT", "Lucida Handwriting",
         "Monotype Corsiva", "Comic Sans MS"],
        "Comic Sans MS",
    )


def ui_font(size, weight="normal", slant="roman"):
    return (UI_FONT_FAMILY, size, weight, slant)


# ============================================================
# Small drawing helpers
# ============================================================

def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_titlebar_image(width, height):
    """Vertical gradient with a glossy highlight band, like Luna title bars."""
    img = Image.new("RGB", (max(width, 1), max(height, 1)))
    draw = ImageDraw.Draw(img)
    split = height * 0.4
    for y in range(height):
        if y < split:
            c = _lerp(TITLEBAR_TOP, TITLEBAR_MID, y / max(split, 1))
        else:
            c = _lerp(TITLEBAR_MID, TITLEBAR_BOTTOM, (y - split) / max(height - split, 1))
        draw.line([(0, y), (width, y)], fill=c)
    return img


def outlined_text(canvas, x, y, text, font, fill="white", outline="black",
                   outline_width=2, anchor="center"):
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            canvas.create_text(x + dx, y + dy, text=text, font=font,
                                fill=outline, anchor=anchor)
    canvas.create_text(x, y, text=text, font=font, fill=fill, anchor=anchor)


# ============================================================
# XPWindow — a draggable, closable pseudo-window
# ============================================================

class XPWindow(tk.Frame):
    """A Luna-styled floating panel: gradient title bar with min/max/close
    buttons, draggable by its title bar, raised to front on click."""

    def __init__(self, parent, title, x, y, width, height,
                 icon_char="\U0001F5CE", body_bg=DIALOG_BG, on_close=None):
        super().__init__(parent, bd=0, highlightthickness=2,
                          highlightbackground=TITLEBAR_BORDER,
                          highlightcolor=TITLEBAR_BORDER, bg=body_bg)
        self.parent = parent
        self._width = width
        self._height = height
        self.body_bg = body_bg
        self.on_close = on_close
        self._drag_data = {"x": None, "y": None}
        self._buttons_left_x = width  # updated once buttons are drawn

        self.place(x=x, y=y, width=width, height=height)

        self.titlebar_h = 24
        self.titlebar = tk.Canvas(self, height=self.titlebar_h,
                                   width=width, highlightthickness=0, bd=0)
        self.titlebar.pack(side="top", fill="x")
        self._draw_titlebar(title, icon_char)

        self.content = tk.Frame(self, bg=body_bg)
        self.content.pack(side="top", fill="both", expand=True)

        self.titlebar.bind("<ButtonPress-1>", self._start_drag)
        self.titlebar.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonPress-1>", lambda e: self.lift())

    # ---------------- title bar drawing ----------------

    def _draw_titlebar(self, title, icon_char):
        img = make_titlebar_image(self._width, self.titlebar_h)
        self._tb_photo = ImageTk.PhotoImage(img)
        self.titlebar.create_image(0, 0, anchor="nw", image=self._tb_photo)
        self.titlebar.create_text(8, self.titlebar_h // 2, anchor="w",
                                   text=icon_char, font=ui_font(10), fill="white")
        self.titlebar.create_text(26, self.titlebar_h // 2, anchor="w",
                                   text=title, font=ui_font(9, "bold"),
                                   fill="white")

        btn_w, gap = 17, 2
        right = self._width - 4
        x1 = right
        x0 = x1 - btn_w
        self._draw_button(x0, x1, "X", CLOSE_FILL, CLOSE_OUTLINE, "close")
        x1 = x0 - gap
        x0 = x1 - btn_w
        self._draw_button(x0, x1, "\u25a1", MINMAX_FILL, MINMAX_OUTLINE, "max")
        x1 = x0 - gap
        x0 = x1 - btn_w
        self._draw_button(x0, x1, "_", MINMAX_FILL, MINMAX_OUTLINE, "min")

        self._buttons_left_x = x0 - 4

    def _draw_button(self, x0, x1, symbol, fill, outline, tag):
        y0, y1 = 3, self.titlebar_h - 3
        self.titlebar.create_rectangle(x0, y0, x1, y1, fill=fill,
                                        outline=outline, tags=tag)
        self.titlebar.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=symbol,
                                   fill="white", font=ui_font(8, "bold"),
                                   tags=tag)
        if tag == "close":
            self.titlebar.tag_bind(tag, "<Button-1>", lambda e: self._close())
        # min/max are decorative only (no window manager to minimize/restore to)

    # ---------------- dragging ----------------

    def _start_drag(self, event):
        if event.x >= self._buttons_left_x:
            return
        self.lift()
        self._drag_data = {"x": event.x, "y": event.y}

    def _on_drag(self, event):
        if self._drag_data["x"] is None:
            return
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        new_x = self.winfo_x() + dx
        new_y = self.winfo_y() + dy
        new_x = max(-self._width + 80, min(new_x, APP_W - 80))
        new_y = max(0, min(new_y, APP_H - 40))
        self.place(x=new_x, y=new_y)

    def _close(self):
        if self.on_close:
            self.on_close()
        self.destroy()


# ============================================================
# XPDialog — small message box (the "Click ok to check your Moots" style)
# ============================================================

class XPDialog(XPWindow):
    def __init__(self, parent, message, buttons, width=340, height=150,
                 x=None, y=None):
        # Use the caller's position when given (needed for stacking several
        # copies of this dialog); otherwise fall back to the original
        # centered-ish default spot.
        if x is None:
            x = 340
        if y is None:
            y = 350
        super().__init__(parent, title="Windows XP", x=x, y=y,
                          width=width, height=height, body_bg=DIALOG_BG)

        icon = tk.Canvas(self.content, width=34, height=150,
                          highlightthickness=0, bg=self.body_bg)
        icon.pack(side="left", padx=(16, 10), pady=(18, 8))
        icon.create_oval(2, 2, 32, 32, fill="#3D6FD6", outline="#1E3F94")
        icon.create_text(17, 17, text="i", font=(UI_FONT_FAMILY, 17, "bold"),
                          fill="white")

        tk.Label(self.content, text=message, font=ui_font(9),
                 bg=self.body_bg, wraplength=width - 90, justify="left")\
            .pack(side="left", pady=(18, 8), anchor="n")

        btn_row = tk.Frame(self.content, bg=self.body_bg)
        btn_row.pack(side="bottom", pady=(0, 14))
        for label, command in buttons:
            tk.Button(btn_row, text=label, width=10, font=ui_font(9),
                       relief="raised", bd=2, bg=self.body_bg,
                       command=lambda c=command: c(self)).pack(side="left", padx=6)


# ============================================================
# XPLoadingDialog — progress bar + Done / Cancel
# ============================================================

class XPLoadingDialog(XPWindow):
    def __init__(self, parent, on_done, on_cancel, width=300, height=150):
        x = (APP_W - width) // 2 + 30
        y = (APP_H - height) // 2 + 30
        super().__init__(parent, title="Windows XP", x=x, y=y,
                          width=width, height=height, body_bg=DIALOG_BG)
        self._on_done_cb = on_done
        self._on_cancel_cb = on_cancel
        self._complete = False
        self._messages = itertools.cycle(PROGRESS_MESSAGES)
        self._offset = 0
        self._anim_job = None
        self._msg_job = None

        tk.Label(self.content, text="Loading...", font=ui_font(9, "bold"),
                 bg=self.body_bg).pack(anchor="w", padx=16, pady=(16, 4))

        self.progress_canvas = tk.Canvas(self.content, height=18,
                                          bg=PROGRESS_BG, highlightthickness=1,
                                          highlightbackground=PROGRESS_BORDER)
        self.progress_canvas.pack(fill="x", padx=16, pady=(0, 4))

        self.status_label = tk.Label(self.content, text=next(self._messages),
                                      font=ui_font(8), fg="#555555",
                                      bg=self.body_bg)
        self.status_label.pack(anchor="w", padx=16, pady=(0, 6))

        btn_row = tk.Frame(self.content, bg=self.body_bg)
        btn_row.pack(side="bottom", pady=(0, 12))
        self.done_btn = tk.Button(btn_row, text="Done", width=8,
                                   state="disabled", font=ui_font(9),
                                   relief="raised", bd=2, bg=self.body_bg,
                                   command=self._handle_done)
        self.done_btn.pack(side="left", padx=6)
        tk.Button(btn_row, text="Cancel", width=8, font=ui_font(9),
                  relief="raised", bd=2, bg=self.body_bg,
                  command=self._handle_cancel).pack(side="left", padx=6)

        self.after(50, self._animate)
        self.after(50, self._cycle_message)

    def _animate(self):
        if not self.winfo_exists():
            return
        self.progress_canvas.delete("block")
        w = self.progress_canvas.winfo_width() or (self._width - 32)
        block_w, gap = 12, 3
        step = block_w + gap
        n = w // step + 2
        for i in range(n):
            x0 = (i * step + self._offset) % (w + step) - step
            self.progress_canvas.create_rectangle(
                x0, 2, x0 + block_w, 16, fill=PROGRESS_BLOCK,
                outline=PROGRESS_BLOCK_EDGE, tags="block")
        self._offset = (self._offset + 3) % step
        self._anim_job = self.after(60, self._animate)

    def _cycle_message(self):
        if not self.winfo_exists():
            return
        self.status_label.config(text=next(self._messages))
        self._msg_job = self.after(1600, self._cycle_message)

    def mark_complete(self):
        self._complete = True
        self.done_btn.config(state="normal")
        self.status_label.config(text="Done collecting data.")
        if self._msg_job:
            self.after_cancel(self._msg_job)
            self._msg_job = None

    def _handle_done(self):
        if not self._complete:
            return
        self._stop()
        self._on_done_cb()

    def _handle_cancel(self):
        self._stop()
        self._on_cancel_cb()

    def _stop(self):
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        if self._msg_job:
            self.after_cancel(self._msg_job)
            self._msg_job = None


# ============================================================
# Result windows
# ============================================================

class XPListWindow(XPWindow):
    """Big window showing a scrollable list of @usernames."""

    def __init__(self, parent, title, usernames, x, y, width=300, height=380):
        super().__init__(parent, title=title, x=x, y=y, width=width,
                          height=height, icon_char="\u2606",
                          body_bg=WINDOW_BODY_BG)

        list_frame = tk.Frame(self.content, bg=WINDOW_BODY_BG)
        list_frame.pack(fill="both", expand=True, padx=6, pady=6)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_frame, font=ui_font(9), bd=1,
                                   relief="sunken", bg="white", fg="black",
                                   activestyle="none",
                                   selectbackground="#316AC5",
                                   selectforeground="white",
                                   yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        if usernames:
            for name in sorted(usernames, key=str.lower):
                self.listbox.insert("end", f"@{name}")
        else:
            self.listbox.insert("end", "  (nobody here — nice!)")
            self.listbox.config(state="disabled")

        self.listbox.bind("<Double-Button-1>", self._open_selected)

    def _open_selected(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        text = self.listbox.get(sel[0]).lstrip("@").strip()
        if text and not text.startswith("("):
            webbrowser.open(f"https://www.instagram.com/{text}/")


class XPStatWindow(XPWindow):
    """Small window showing a single big number."""

    def __init__(self, parent, title, value, x, y, width=230, height=95):
        super().__init__(parent, title=title, x=x, y=y, width=width,
                          height=height, icon_char="\u2605",
                          body_bg=DIALOG_BG)
        tk.Label(self.content, text=str(value),
                 font=(UI_FONT_FAMILY, 26, "bold"),
                 bg=self.body_bg, fg="#0A246A").pack(expand=True)


# ============================================================
# Main application
# ============================================================

class MootCheckApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MootCheck")
        self.root.geometry(f"{APP_W}x{APP_H}")
        self.root.resizable(False, False)

        resolve_fonts()

        self.results = None
        self._cancelled = False
        self.loading_dialog = None
        self.result_windows = []
        self._intro_dialogs = []

        self._build_desktop()
        self.root.after(150, self._show_intro_dialog)

    # ---------------- desktop / wallpaper / logo ----------------

    def _build_desktop(self):
        self.bg_canvas = tk.Canvas(self.root, width=APP_W, height=APP_H,
                                    highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, width=APP_W, height=APP_H)

        wallpaper = Image.open(WALLPAPER_PATH).convert("RGB").resize((APP_W, APP_H))
        self._wallpaper_photo = ImageTk.PhotoImage(wallpaper)
        self.bg_canvas.create_image(0, 0, anchor="nw", image=self._wallpaper_photo)

#self._draw_logo()

    def _draw_logo(self):
        logo_font = (LOGO_FONT_FAMILY, 46, "bold")
        sub_font = ui_font(11, "bold")

        outlined_text(self.bg_canvas, 150, 90, "MOOT", logo_font,
                       fill="white", outline="black", outline_width=2,
                       anchor="w")
        outlined_text(self.bg_canvas, 190, 150, "CHECKER", logo_font,
                       fill="white", outline="black", outline_width=2,
                       anchor="w")
        outlined_text(self.bg_canvas, 330, 85, "moots daw pero",
                       ui_font(11, "bold"), fill="white", outline="black",
                       outline_width=1, anchor="w")
        outlined_text(self.bg_canvas, 330, 102, "inunfollow ako??",
                       ui_font(11, "bold"), fill="white", outline="black",
                       outline_width=1, anchor="w")
        outlined_text(self.bg_canvas, 150, 170, "meet, matt", sub_font,
                       fill="white", outline="black", outline_width=1,
                       anchor="w")
        outlined_text(self.bg_canvas, 150, 186, "— the builder.", sub_font,
                       fill="white", outline="black", outline_width=1,
                       anchor="w")

    # ---------------- flow: intro -> loading -> results ----------------

    def _show_intro_dialog(self):
        """Show the "Click ok to check your Moots" dialog as a cascaded
        stack of three copies (back two are decorative/peeking, exactly
        like the reference screenshot). Only the front-most copy (drawn
        last, offset the least) is the one that actually advances the
        flow when its "okay" is clicked."""
        self._cancelled = False

        # Clean up any leftover copies from a previous cancel/error retry.
        for d in self._intro_dialogs:
            if d.winfo_exists():
                d.destroy()
        self._intro_dialogs = []

        base_x, base_y = 340, 350
        offset_x, offset_y = 26, 22
        copies = 3

        # Build back-to-front: the most-offset copy is placed first (so it
        # ends up furthest back / bottom of the stack), and the least-offset
        # copy — sitting at base_x/base_y — is placed last, landing on top
        # exactly like the original single dialog used to.
        for i in range(copies - 1, -1, -1):
            is_front = (i == 0)
            dlg = XPDialog(
                self.root,
                message='Click "ok" to check your Moots.',
                buttons=[("okay", self._handle_ok if is_front else self._raise_stacked_dialog)],
                x=base_x + i * offset_x,
                y=base_y + i * offset_y,
            )
            self._intro_dialogs.append(dlg)

    def _raise_stacked_dialog(self, dialog):
        # The two background copies aren't meant to progress the flow —
        # they're just there for the cascaded look — so clicking their
        # "okay" (reachable only if manually raised) just brings that copy
        # to the front instead of doing anything else.
        dialog.lift()

    def _handle_ok(self, dialog):
        for d in self._intro_dialogs:
            if d.winfo_exists():
                d.destroy()
        self._intro_dialogs = []

        self.loading_dialog = XPLoadingDialog(
            self.root, on_done=self._show_results, on_cancel=self._handle_cancel
        )
        threading.Thread(target=self._run_check_thread, daemon=True).start()

    def _run_check_thread(self):
        try:
            results = run_mootcheck()
            self.root.after(0, lambda: self._on_check_complete(results))
        except Exception as e:
            self.root.after(0, lambda err=e: self._on_check_error(err))

    def _on_check_complete(self, results):
        self.results = results
        if not self._cancelled and self.loading_dialog is not None \
                and self.loading_dialog.winfo_exists():
            self.loading_dialog.mark_complete()

    def _on_check_error(self, error):
        if self._cancelled or self.loading_dialog is None:
            return
        if self.loading_dialog.winfo_exists():
            self.loading_dialog._stop()
            self.loading_dialog.destroy()
        self.loading_dialog = None
        XPDialog(
            self.root,
            message=f"Something went wrong:\n{error}",
            buttons=[("okay", lambda d: (d.destroy(), self._show_intro_dialog()))],
        )

    def _handle_cancel(self):
        self._cancelled = True
        self.loading_dialog = None
        self._show_intro_dialog()

    def _show_results(self):
        if self.loading_dialog is not None and self.loading_dialog.winfo_exists():
            self.loading_dialog.destroy()
        self.loading_dialog = None

        for win in self.result_windows:
            if win.winfo_exists():
                win.destroy()
        self.result_windows = []

        results = self.results
        not_back = results["not_following_back"]
        you_dont = results["followers_you_dont_follow"]

        w1 = XPListWindow(self.root, "Accounts that don't follow you back",
                           not_back, x=50, y=70, width=310, height=400)
        w2 = XPListWindow(self.root, "accounts that you don't follow back",
                           you_dont, x=130, y=140, width=310, height=400)
        self.result_windows += [w1, w2]

        stats = [
            ("followers", len(results["followers"])),
            ("following", len(results["following"])),
            ("mutuals", len(results["mutuals"])),
            ("accounts that don't follow you back", len(not_back)),
            ("accounts that you don't follow back", len(you_dont)),
        ]
        base_x, base_y = 630, 30
        for i, (label, value) in enumerate(stats):
            win = XPStatWindow(self.root, label, value,
                                x=base_x + i * 14, y=base_y + i * 100,
                                width=280, height=90)
            self.result_windows.append(win)

    # ---------------- run ----------------

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MootCheckApp()
    app.run()