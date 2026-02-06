"""Terminal UI utilities for saas-radar skill."""

import sys
import time
import threading
import random
from typing import Optional

# Check if we're in a real terminal (not captured by Claude Code)
IS_TTY = sys.stderr.isatty()

# ANSI color codes
class Colors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


MINI_BANNER = f"""{Colors.GREEN}{Colors.BOLD}/saasradar{Colors.RESET} {Colors.DIM}· scanning for SaaS ideas...{Colors.RESET}"""

# Fun status messages for each phase
GROWTH_MESSAGES = [
    "Scanning subreddit growth signals...",
    "Measuring community acceleration...",
    "Analyzing posting velocity...",
    "Checking subreddit vitality...",
    "Finding fast-growing communities...",
]

REDDIT_MESSAGES = [
    "Hunting for SaaS pain points...",
    "Scanning Reddit for wish-list posts...",
    "Finding 'I wish there was a tool' threads...",
    "Discovering what people want to automate...",
    "Reading what builders are discussing...",
]

X_MESSAGES = [
    "Checking indie hacker tweets...",
    "Finding 'someone build this' posts...",
    "Scanning SaaS builder discussions...",
    "Discovering what makers are shipping...",
    "Reading the builder timeline...",
]

ENRICHING_MESSAGES = [
    "Getting the juicy details...",
    "Fetching engagement metrics...",
    "Reading top comments...",
    "Extracting insights...",
    "Analyzing discussions...",
]

PROCESSING_MESSAGES = [
    "Clustering similar ideas...",
    "Scoring market signals...",
    "Ranking SaaS opportunities...",
    "Removing duplicates...",
    "Computing growth-weighted scores...",
]

# Spinner frames
SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']


class Spinner:
    """Animated spinner for long-running operations."""

    def __init__(self, message: str = "Working", color: str = Colors.CYAN):
        self.message = message
        self.color = color
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_idx = 0
        self.shown_static = False

    def _spin(self):
        while self.running:
            frame = SPINNER_FRAMES[self.frame_idx % len(SPINNER_FRAMES)]
            sys.stderr.write(f"\r{self.color}{frame}{Colors.RESET} {self.message}  ")
            sys.stderr.flush()
            self.frame_idx += 1
            time.sleep(0.08)

    def start(self):
        self.running = True
        if IS_TTY:
            # Real terminal - animate
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        else:
            # Not a TTY (Claude Code) - just print once
            if not self.shown_static:
                sys.stderr.write(f"⏳ {self.message}\n")
                sys.stderr.flush()
                self.shown_static = True

    def update(self, message: str):
        self.message = message
        if not IS_TTY and not self.shown_static:
            sys.stderr.write(f"⏳ {message}\n")
            sys.stderr.flush()

    def stop(self, final_message: str = ""):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)
        if IS_TTY:
            sys.stderr.write("\r" + " " * 80 + "\r")
        if final_message:
            sys.stderr.write(f"✓ {final_message}\n")
        sys.stderr.flush()


class ProgressDisplay:
    """Progress display for research phases."""

    def __init__(self, topic: str, show_banner: bool = True):
        self.topic = topic
        self.spinner: Optional[Spinner] = None
        self.start_time = time.time()

        if show_banner:
            self._show_banner()

    def _show_banner(self):
        if IS_TTY:
            sys.stderr.write(MINI_BANNER + "\n")
            sys.stderr.write(f"{Colors.DIM}Topic: {Colors.RESET}{Colors.BOLD}{self.topic}{Colors.RESET}\n\n")
        else:
            sys.stderr.write(f"/saasradar · scanning: {self.topic}\n")
        sys.stderr.flush()

    def start_growth_scan(self):
        msg = random.choice(GROWTH_MESSAGES)
        self.spinner = Spinner(f"{Colors.GREEN}Growth{Colors.RESET} {msg}", Colors.GREEN)
        self.spinner.start()

    def update_growth_scan(self, current: int, total: int):
        if self.spinner:
            msg = random.choice(GROWTH_MESSAGES)
            self.spinner.update(f"{Colors.GREEN}Growth{Colors.RESET} [{current}/{total}] {msg}")

    def end_growth_scan(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.GREEN}Growth{Colors.RESET} Scanned {count} subreddits")

    def start_reddit(self):
        msg = random.choice(REDDIT_MESSAGES)
        self.spinner = Spinner(f"{Colors.YELLOW}Reddit{Colors.RESET} {msg}", Colors.YELLOW)
        self.spinner.start()

    def end_reddit(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.YELLOW}Reddit{Colors.RESET} Found {count} threads")

    def start_reddit_enrich(self, current: int, total: int):
        if self.spinner:
            self.spinner.stop()
        msg = random.choice(ENRICHING_MESSAGES)
        self.spinner = Spinner(f"{Colors.YELLOW}Reddit{Colors.RESET} [{current}/{total}] {msg}", Colors.YELLOW)
        self.spinner.start()

    def update_reddit_enrich(self, current: int, total: int):
        if self.spinner:
            msg = random.choice(ENRICHING_MESSAGES)
            self.spinner.update(f"{Colors.YELLOW}Reddit{Colors.RESET} [{current}/{total}] {msg}")

    def end_reddit_enrich(self):
        if self.spinner:
            self.spinner.stop(f"{Colors.YELLOW}Reddit{Colors.RESET} Enriched with engagement data")

    def start_x(self):
        msg = random.choice(X_MESSAGES)
        self.spinner = Spinner(f"{Colors.CYAN}X{Colors.RESET} {msg}", Colors.CYAN)
        self.spinner.start()

    def end_x(self, count: int):
        if self.spinner:
            self.spinner.stop(f"{Colors.CYAN}X{Colors.RESET} Found {count} posts")

    def start_processing(self):
        msg = random.choice(PROCESSING_MESSAGES)
        self.spinner = Spinner(f"{Colors.PURPLE}Processing{Colors.RESET} {msg}", Colors.PURPLE)
        self.spinner.start()

    def end_processing(self):
        if self.spinner:
            self.spinner.stop()

    def show_complete(self, item_count: int, growth_count: int):
        elapsed = time.time() - self.start_time
        if IS_TTY:
            sys.stderr.write(f"\n{Colors.GREEN}{Colors.BOLD}✓ SaaS Radar complete{Colors.RESET} ")
            sys.stderr.write(f"{Colors.DIM}({elapsed:.1f}s){Colors.RESET}\n")
            sys.stderr.write(f"  {Colors.GREEN}Ideas:{Colors.RESET} {item_count}  ")
            sys.stderr.write(f"{Colors.GREEN}Subreddits:{Colors.RESET} {growth_count}\n\n")
        else:
            sys.stderr.write(f"✓ SaaS Radar complete ({elapsed:.1f}s) - {item_count} ideas, {growth_count} subreddits\n")
        sys.stderr.flush()

    def show_error(self, message: str):
        sys.stderr.write(f"{Colors.RED}✗ Error:{Colors.RESET} {message}\n")
        sys.stderr.flush()

    def show_promo(self, missing: str = "both"):
        """Show promotional message for missing API keys."""
        if missing == "both":
            msg = (
                "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "No API keys configured. Add keys to ~/.config/saas-radar/.env\n"
                "  OPENAI_API_KEY → Reddit threads with real upvotes & comments\n"
                "  XAI_API_KEY    → X posts with real likes & reposts\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        elif missing == "x":
            msg = "\n💡 Tip: Add XAI_API_KEY to ~/.config/saas-radar/.env for X/Twitter data!\n"
        elif missing == "reddit":
            msg = "\n💡 Tip: Add OPENAI_API_KEY to ~/.config/saas-radar/.env for Reddit data!\n"
        else:
            return
        sys.stderr.write(msg)
        sys.stderr.flush()
