from __future__ import annotations

import logging
import threading
import time
from typing import List, Optional, Dict
import os

import tkinter as tk
from tkinter import messagebox, filedialog, ttk as tk_ttk

# Preserve all functionality by building atop the frozen frontpage variant.
from offline_chatbot_programs_frontpage_preserved import (
    ProgramsFrontpageUI,
    ProgramRecord,
    ProgramStep,
    ProgramStore,
)

logger = logging.getLogger("offline_chatbot.programs_modern_ui")


class ProgramsModernUI(ProgramsFrontpageUI):
    """
    Modernized UI variant:
      - Retains Programs-first frontpage flow and ProgramStore semantics
      - Applies a modern dark theme (ttkbootstrap theme if available; otherwise styled Tk)
      - Re-skins underlying legacy chat widgets (transcript, entry, send) without altering preserved behavior
      - Uses a Treeview-based programs list for a contemporary look
    """

    def __init__(self, seed_text: Optional[str] = None, show_seed: bool = False, seed_delay_ms: int = 250):
        # super() will call our overridden _build_frontpage(), which calls _apply_modern_theme()
        super().__init__()
        try:
            self.title("Offline LM Studio — Programs (Modern UI)")
        except Exception:
            pass

        # Treeview mapping holder (may be set by _build_frontpage)
        self._frontpage_tree: Optional[tk_ttk.Treeview] = getattr(self, "_frontpage_tree", None)
        self._fp_mapping: Dict[str, str] = getattr(self, "_fp_mapping", {})  # iid -> program name

        # Seeding configuration
        self._seed_text = (seed_text or "").strip()
        try:
            self._seed_delay_ms = max(0, int(seed_delay_ms))
        except Exception:
            self._seed_delay_ms = 250
        self._show_seed = bool(show_seed)

        # Announce seeding status; schedule after overlay dismissal (post-frontpage)
        try:
            if self._seed_text:
                if self._show_seed:
                    self._append("— Welcome seeding enabled (showing configured seed): —\n", "sys")
                    self._append(self._seed_text + "\n", "sys")
                else:
                    self._append("— Welcome seeding enabled. —\n", "sys")
                # do not start now; mark pending and trigger when frontpage hides
                self._pending_welcome_seed = True
            else:
                self._append("— Tip: launch with --seed-prompt \"...\" or set env CHATBOT_SEED_PROMPT to auto-generate a welcome message. —\n", "sys")
        except Exception:
            pass

        # After base has constructed widgets, skin legacy chat controls
        try:
            self.after(200, self._skin_legacy_chat_widgets)
        except Exception:
            pass

    # ---------- Theming ----------

    def _apply_modern_theme(self) -> None:
        """Apply a dark, modern theme with graceful fallback and safety flag."""
        # Safety flag: only use ttkbootstrap if fully initialized
        self._use_ttkb = False
        try:
            self.configure(bg="#0f1113")
        except Exception:
            pass

        # Try optional ttkbootstrap only when explicitly enabled via env CHATBOT_USE_TTKBOOTSTRAP
        enable = False
        try:
            import os as _os
            enable = str(_os.environ.get("CHATBOT_USE_TTKBOOTSTRAP", "")).lower() in ("1", "true", "yes", "on")
        except Exception:
            enable = False

        if enable:
            try:
                import ttkbootstrap as _ttkb  # type: ignore
                from ttkbootstrap.constants import (  # type: ignore
                    PRIMARY as _PRIMARY,
                    SECONDARY as _SECONDARY,
                    INFO as _INFO,
                    DANGER as _DANGER,
                )
                # Initialize with a known-safe theme if available
                style = _ttkb.Style()
                try:
                    names = {str(n).lower() for n in (style.theme_names() or [])}
                except Exception:
                    names = set()
                safe = ["flatly", "cyborg", "darkly", "superhero", "vapor", "morph", "solar"]
                chosen = next((n for n in safe if n in names), None)
                if chosen:
                    try:
                        style.theme_use(chosen)
                    except Exception:
                        pass

                # Cache for conditional widget styling
                self._ttkb = _ttkb
                self._ttk_style = style
                self._ttkb_PRIMARY = _PRIMARY
                self._ttkb_SECONDARY = _SECONDARY
                self._ttkb_INFO = _INFO
                self._ttkb_DANGER = _DANGER
                self._use_ttkb = True
            except Exception as e:
                try:
                    logger.debug("ttkbootstrap init skipped or failed: %s", e)
                except Exception:
                    pass

        if not self._use_ttkb:
            # Tk fallback defaults for a cohesive dark look
            try:
                self.option_add("*Font", "{Segoe UI} 10")
                self.option_add("*Background", "#0f1113")
                self.option_add("*Foreground", "#e6e6e6")
                self.option_add("*Entry.Background", "#1b1e22")
                self.option_add("*Entry.Foreground", "#e6e6e6")
                self.option_add("*Button.Background", "#2563eb")
                self.option_add("*Button.Foreground", "#ffffff")
            except Exception:
                pass

    # ---------- Frontpage (overridden with modern layout) ----------

    def _build_frontpage(self) -> None:
        """Modern Programs overlay replacing the legacy Listbox with a Treeview."""
        # Ensure theme readiness
        self._apply_modern_theme()

        # If base constructed an overlay already, replace it cleanly
        try:
            if getattr(self, "_frontpage", None):
                self._frontpage.destroy()
        except Exception:
            pass

        # Build modern overlay using Tk widgets; optionally style buttons with ttkbootstrap if available
        root = self
        overlay = tk.Frame(root, bg="#0f1113")
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self._frontpage = overlay

        container = tk.Frame(overlay, bg="#0f1113")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Header
        hdr = tk.Frame(container, bg="#0f1113")
        hdr.pack(fill="x", pady=(0, 12))
        title = tk.Label(hdr, text="Programs", font=("{Segoe UI}", 22, "bold"), fg="#e6e6e6", bg="#0f1113")
        subt = tk.Label(
            hdr,
            text="Choose a program to auto-prime, or create one.",
            font=("{Segoe UI}", 10),
            fg="#a1a1aa",
            bg="#0f1113",
        )
        title.pack(anchor="w")
        subt.pack(anchor="w")

        body = tk.Frame(container, bg="#0f1113")
        body.pack(fill="both", expand=True)

        # Left: Programs list as a modern Treeview
        left = tk.Frame(body, bg="#0f1113")
        left.pack(side="left", fill="both", expand=True)

        tree = tk_ttk.Treeview(left, columns=("name", "created"), show="headings", height=16)
        tree.heading("name", text="Program")
        tree.heading("created", text="Created")
        tree.column("name", width=320, anchor="w")
        tree.column("created", width=160, anchor="w")
        ysb = tk_ttk.Scrollbar(left, orient="vertical", command=tree.yview)
        tree.configure(yscroll=ysb.set)
        tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        tree.bind("<Double-Button-1>", lambda e: self._run_selected_program())

        # Assign modern list refs
        self._frontpage_tree = tree
        self._fp_mapping = {}
        self._frontpage_list = None  # ensure base listbox logic is bypassed

        self._frontpage_empty_label = tk.Label(left, text="", fg="#8b8b8b", bg="#0f1113")
        self._frontpage_empty_label.pack(anchor="w", pady=(6, 0))

        # Right: Modern action buttons
        right = tk.Frame(body, bg="#0f1113")
        right.pack(side="right", fill="y", padx=(12, 0))

        def mkbtn(text: str, cmd, bootstyle=None):
            if getattr(self, "_use_ttkb", False) and hasattr(self, "_ttkb"):
                try:
                    b = self._ttkb.Button(right, text=text, command=cmd, bootstyle=bootstyle, width=22)  # type: ignore
                    b.pack(anchor="n", pady=(0, 8))
                    return b
                except Exception:
                    pass
            # Fallback Tk button
            b = tk.Button(right, text=text, command=cmd, width=24, bg="#2563eb", fg="#ffffff", relief="flat")
            b.pack(anchor="n", pady=(0, 8))
            return b

        mkbtn("Run Program", self._run_selected_program, getattr(self, "_ttkb_PRIMARY", None))
        mkbtn("Create Program", self._create_program_quick, getattr(self, "_ttkb_SECONDARY", None))
        mkbtn("Manage Programs", self._open_manage_then_refresh, getattr(self, "_ttkb_INFO", None))

        if getattr(self, "_use_ttkb", False) and hasattr(self, "_ttkb"):
            try:
                self._ttkb.Button(  # type: ignore
                    right, text="Exit", command=self.destroy, bootstyle=getattr(self, "_ttkb_DANGER", None), width=22
                ).pack(anchor="s", pady=(180, 0))
            except Exception:
                tk.Button(
                    right, text="Exit", command=self.destroy, width=24, bg="#ef4444", fg="#ffffff", relief="flat"
                ).pack(anchor="s", pady=(180, 0))
        else:
            tk.Button(
                right, text="Exit", command=self.destroy, width=24, bg="#ef4444", fg="#ffffff", relief="flat"
            ).pack(anchor="s", pady=(180, 0))

        # Populate with saved programs
        self._refresh_frontpage_list()

    def _refresh_frontpage_list(self) -> None:
        """Populate modern Treeview (or fallback to base listbox)."""
        if getattr(self, "_frontpage_tree", None) is not None:
            tree = self._frontpage_tree
            # Clear rows
            for iid in tree.get_children():
                tree.delete(iid)
            self._fp_mapping = {}

            names = self.program_store.list_names()
            for n in names:
                rec = self.program_store.get(n)
                created = getattr(rec, "created_at", "") if rec else ""
                iid = tree.insert("", "end", values=(n, created))
                self._fp_mapping[iid] = n

            if names:
                self._frontpage_empty_label.configure(text="")
            else:
                self._frontpage_empty_label.configure(text="No programs found. Click 'Create Program' to add one.")
        else:
            # Use preserved behavior (Listbox)
            try:
                super()._refresh_frontpage_list()
            except Exception:
                pass

    # ---------- Selection helpers ----------

    def _get_selected_program_name(self) -> Optional[str]:
        if getattr(self, "_frontpage_tree", None) is not None:
            sel = self._frontpage_tree.selection()
            if not sel:
                return None
            iid = sel[0]
            return self._fp_mapping.get(iid)
        else:
            if not getattr(self, "_frontpage_list", None):
                return None
            sel = self._frontpage_list.curselection()
            if not sel:
                return None
            return self._frontpage_list.get(sel[0])

    def _run_selected_program(self) -> None:
        name = self._get_selected_program_name()
        if not name:
            try:
                messagebox.showinfo("Programs", "Select a program to run.")
            except Exception:
                pass
            return
        self._hide_frontpage()
        self._run_program_by_name(name)

    def _hide_frontpage(self) -> None:
        """
        Override to schedule welcome seeding after the frontpage overlay is dismissed.
        """
        try:
            super()._hide_frontpage()
        finally:
            # If seeding was configured, try to fire once chat is visible and idle
            if getattr(self, "_seed_text", ""):
                # mark pending and schedule first check after the configured delay
                try:
                    self._pending_welcome_seed = True
                except Exception:
                    self._pending_welcome_seed = True
                try:
                    self.after(max(0, int(getattr(self, "_seed_delay_ms", 250))), self._try_fire_welcome_seed)
                except Exception:
                    # fallback small delay
                    self.after(300, self._try_fire_welcome_seed)

    def _try_fire_welcome_seed(self) -> None:
        """
        Fire welcome seeding only after the frontpage overlay is hidden and no stream is running.
        If conditions are not met, reschedule a short recheck.
        """
        # Only once
        if not getattr(self, "_seed_text", "") or not getattr(self, "_pending_welcome_seed", False):
            return
        # Overlay still visible?
        overlay_active = False
        front = getattr(self, "_frontpage", None)
        try:
            if front is not None and str(front.winfo_manager() or "") != "":
                overlay_active = True
        except Exception:
            overlay_active = False
        if overlay_active or getattr(self, "streaming", False):
            # Try again shortly
            try:
                self.after(300, self._try_fire_welcome_seed)
            except Exception:
                pass
            return
        # Fire once
        self._pending_welcome_seed = False
        self._start_seeding()

    # ---------- Legacy chat skinning (non-destructive) ----------

    def _skin_legacy_chat_widgets(self) -> None:
        """
        Best-effort modern skin for underlying chat widgets created by the preserved base.
        This does NOT change behavior; only updates visuals.
        """
        try:
            widgets: List[tk.Widget] = []

            def walk(w):
                for c in w.winfo_children():
                    # Skip the frontpage overlay
                    if c is getattr(self, "_frontpage", None):
                        continue
                    widgets.append(c)
                    walk(c)

            walk(self)

            text_candidates = [w for w in widgets if isinstance(w, tk.Text)]
            entry_candidates = [w for w in widgets if isinstance(w, tk.Entry)]
            button_candidates = [w for w in widgets if isinstance(w, tk.Button)]

            # Choose the largest Text widget as transcript
            transcript = None
            if text_candidates:
                transcript = max(
                    text_candidates, key=lambda w: (w.winfo_width() or 1) * (w.winfo_height() or 1)
                )

            if transcript:
                try:
                    transcript.configure(
                        bg="#0f1113",
                        fg="#e6e6e6",
                        insertbackground="#e6e6e6",
                        highlightthickness=0,
                        relief="flat",
                        padx=8,
                        pady=8,
                    )
                    # Common tags from preserved code
                    try:
                        transcript.tag_configure("sys", foreground="#8ab4f8")
                    except Exception:
                        pass
                    try:
                        transcript.tag_configure("bot", foreground="#c7f296")
                    except Exception:
                        pass
                    try:
                        transcript.tag_configure("user", foreground="#ffbf7f")
                    except Exception:
                        pass
                except Exception:
                    pass

            # Style the entry
            if entry_candidates:
                ent = entry_candidates[0]
                try:
                    ent.configure(
                        bg="#1b1e22",
                        fg="#e6e6e6",
                        insertbackground="#e6e6e6",
                        relief="flat",
                        highlightthickness=1,
                        highlightbackground="#2a2f36",
                        highlightcolor="#3b82f6",
                    )
                except Exception:
                    pass

            # Style the send button (heuristic if attribute missing)
            btn = getattr(self, "send_btn", None)
            if not isinstance(btn, tk.Button) and button_candidates:
                # Choose the lowest button on the window as likely "Send"
                btn = max(button_candidates, key=lambda w: w.winfo_y())
            if isinstance(btn, tk.Button):
                try:
                    btn.configure(
                        bg="#2563eb",
                        fg="#ffffff",
                        activebackground="#1d4ed8",
                        activeforeground="#ffffff",
                        relief="flat",
                        bd=0,
                        padx=12,
                        pady=6,
                        highlightthickness=0,
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.exception("Modern skinning failed: %s", e)

        # ---------- Startup welcome seeding ----------
        def _start_seeding(self) -> None:
            if getattr(self, "streaming", False) or not getattr(self, "_seed_text", ""):
                return
            try:
                self._append("Bot: ", "bot")
                self.streaming = True
                try:
                    self.send_btn.config(state="disabled")
                except Exception:
                    pass
                threading.Thread(target=self._seed_worker, args=(self._seed_text,), daemon=True).start()
            except Exception:
                # fail silently; keep UI usable
                pass

        def _seed_worker(self, text: str) -> None:
            try:
                self.backend.respond_stream(text, on_token=lambda tok: self.after(0, self._append, tok, "bot"))
            except Exception as e:
                def err():
                    self._append("\n[Error: failed to generate welcome message]\n", "sys")
                    try:
                        messagebox.showerror("Welcome Error", str(e))
                    except Exception:
                        pass
                self.after(0, err)
            finally:
                def done():
                    self._append("\n", "bot")
                    self.streaming = False
                    try:
                        self.send_btn.config(state="normal")
                    except Exception:
                        pass
                self.after(0, done)


def _resolve_seed_from_args_env(args) -> Optional[str]:
    """
    Seed resolution priority:
      1) --skip-seed (disables seeding)
      2) --seed-prompt
      3) --seed-file
      4) --seed-env (name of env var to read)
      5) CHATBOT_SEED_PROMPT (default env var)
    """
    if getattr(args, "skip_seed", False):
        return None
    # direct text
    if getattr(args, "seed_prompt", None):
        return args.seed_prompt
    # file
    if getattr(args, "seed_file", None):
        try:
            from pathlib import Path as _Path
            p = _Path(args.seed_file)
            if p.exists():
                return p.read_text(encoding="utf-8")
        except Exception as e:
            logger.exception("Failed to read seed file: %s", e)
    # env var name or default
    env_name = getattr(args, "seed_env", None) or "CHATBOT_SEED_PROMPT"
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    return None


def _build_arg_parser():
    import argparse as _argparse
    parser = _argparse.ArgumentParser(description="Offline LM Studio Programs (Modern UI) with optional welcome seeding")
    parser.add_argument("--seed-prompt", dest="seed_prompt", type=str, help="Seed prompt text to generate a welcome message")
    parser.add_argument("--seed-file", dest="seed_file", type=str, help="Path to a text file containing the seed prompt")
    parser.add_argument("--seed-env", dest="seed_env", type=str, help="Environment variable name holding the seed prompt (default: CHATBOT_SEED_PROMPT)")
    parser.add_argument("--seed-delay", dest="seed_delay", type=int, default=250, help="Delay in ms before triggering the welcome seeding (default: 250)")
    parser.add_argument("--show-seed", dest="show_seed", action="store_true", help="Also display the configured seed text in the transcript (as system text)")
    parser.add_argument("--skip-seed", dest="skip_seed", action="store_true", help="Disable seeding even if env/file/arg is provided")
    return parser


if __name__ == "__main__":
    try:
        parser = _build_arg_parser()
        args = parser.parse_args()
        seed_text = _resolve_seed_from_args_env(args)
        app = ProgramsModernUI(seed_text=seed_text, show_seed=getattr(args, "show_seed", False), seed_delay_ms=getattr(args, "seed_delay", 250))
        app.mainloop()
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        try:
            messagebox.showerror("Fatal Error", str(e))
        except Exception:
            pass