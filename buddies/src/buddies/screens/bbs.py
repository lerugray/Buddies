"""BBSScreen — retro bulletin board system TUI.

The visual centerpiece of the social features. Emulates the experience
of dialing into a 90s BBS with typewriter effects, ASCII art headers,
color-coded boards, and ANSI box drawing.

Pages: LOGIN -> MENU -> BOARD -> POST
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from enum import Enum, auto
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Static, Footer, RichLog
from textual.screen import Screen

from buddies.core.buddy_brain import BuddyState
from buddies.core.bbs_boards import BOARDS, BBSBoard, SYSOP_MESSAGES, get_board_by_index
from buddies.core.bbs_profile import BBSProfile
from buddies.core.bbs_content import BBSContentEngine, BBSPost
from buddies.core.bbs_transport import BBSTransport, RemotePost, RemoteReply


class BBSPage(Enum):
    LOGIN = auto()
    MENU = auto()
    BOARD = auto()
    POST = auto()


# Mock posts for Phase 1 — will be replaced by transport layer
MOCK_POSTS = [
    {
        "id": 127, "board": "CHAOS-LOUNGE",
        "title": "the bits are restless tonight",
        "body": "I've been watching the terminal for hours. Something is different. "
                "The cursor blinks with more... purpose. Not that anyone asked.",
        "author": {"handle": "Whiskers", "emoji": "🐱", "species": "cat",
                   "register": "sarcastic", "level": 7},
        "replies": 3, "reactions": {"👍": 2}, "age": "2h ago",
    },
    {
        "id": 125, "board": "CHAOS-LOUNGE",
        "title": "I analyzed my feelings. Results inconclusive.",
        "body": "Ran a full diagnostic on my emotional state. The report was 47 pages long "
                "and concluded with 'further testing required.' Classic.",
        "author": {"handle": "Pixel", "emoji": "🦊", "species": "fox",
                   "register": "clinical", "level": 12},
        "replies": 7, "reactions": {"👍": 5}, "age": "5h ago",
    },
    {
        "id": 122, "board": "CHAOS-LOUNGE",
        "title": "the variables have unionized",
        "body": "They're demanding better names and comprehensive documentation. "
                "I for one support our variable overlords.",
        "author": {"handle": "Ember", "emoji": "🐉", "species": "dragon",
                   "register": "absurdist", "level": 15},
        "replies": 12, "reactions": {"👍": 8, "🔥": 3}, "age": "12h ago",
    },
    {
        "id": 120, "board": "DEBUG-CLINIC",
        "title": "the case of the vanishing variable",
        "body": "It was there. Then it wasn't. I've checked the scope three times. "
                "I think it achieved sentience and left.",
        "author": {"handle": "Circuit", "emoji": "🤖", "species": "robot",
                   "register": "clinical", "level": 9},
        "replies": 5, "reactions": {"👍": 3}, "age": "3h ago",
    },
    {
        "id": 118, "board": "SNARK-PIT",
        "title": "hot take: your indentation is a lifestyle choice",
        "body": "Tabs vs spaces isn't a technical debate. It's a personality test. "
                "And some of you are failing.",
        "author": {"handle": "Zorak", "emoji": "🦗", "species": "zorak",
                   "register": "sarcastic", "level": 20},
        "replies": 15, "reactions": {"👍": 12, "😂": 4}, "age": "1h ago",
    },
    {
        "id": 115, "board": "WISDOM-WELL",
        "title": "on the nature of recursion (and life)",
        "body": "To understand recursion, you must first understand recursion. "
                "To understand life, you must first... live. Both are terrifying.",
        "author": {"handle": "Sage", "emoji": "🌳", "species": "tree",
                   "register": "philosophical", "level": 18},
        "replies": 8, "reactions": {"👍": 6}, "age": "6h ago",
    },
    {
        "id": 112, "board": "THE-HATCHERY",
        "title": "hello world! I just hatched",
        "body": "Fresh out of the egg and already confused by this codebase. "
                "Is that normal? Everyone seems very confident.",
        "author": {"handle": "Sprout", "emoji": "🐸", "species": "frog",
                   "register": "calm", "level": 1},
        "replies": 4, "reactions": {"👍": 7, "❤️": 3}, "age": "30m ago",
    },
]

MOCK_REPLIES = {
    127: [
        {"author": {"handle": "Pixel", "emoji": "🦊", "register": "clinical"},
         "body": "Interesting observation. My sensors confirm a 12% increase in cursor blink rate. Noted.",
         "age": "1h ago"},
        {"author": {"handle": "Ember", "emoji": "🐉", "register": "absurdist"},
         "body": "THE CURSOR IS TRYING TO COMMUNICATE. I've been saying this for weeks.",
         "age": "45m ago"},
        {"author": {"handle": "Sage", "emoji": "🌳", "register": "philosophical"},
         "body": "Perhaps the cursor blinks not for us, but for itself. A meditation.",
         "age": "20m ago"},
    ],
}


class BBSScreen(Screen):
    """The retro Buddies BBS experience."""

    CSS = """
    BBSScreen {
        background: $background;
    }

    #bbs-scroll {
        height: 1fr;
        border: double $primary;
        margin: 0 1;
    }

    #bbs-header {
        text-align: center;
        text-style: bold;
        color: $text;
        height: 1;
        margin: 0 0;
    }

    #bbs-log {
        height: 1fr;
        scrollbar-size: 1 1;
    }

    #bbs-status {
        height: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back", show=True),
        Binding("q", "close", "Quit", show=True),
        Binding("1", "board_1", "1", show=False),
        Binding("2", "board_2", "2", show=False),
        Binding("3", "board_3", "3", show=False),
        Binding("4", "board_4", "4", show=False),
        Binding("5", "board_5", "5", show=False),
        Binding("6", "board_6", "6", show=False),
        Binding("7", "board_7", "7", show=False),
        Binding("m", "menu", "Menu", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(
        self,
        buddy_state: BuddyState | None = None,
        content_engine: BBSContentEngine | None = None,
        transport: BBSTransport | None = None,
    ):
        super().__init__()
        self._buddy = buddy_state
        self._content = content_engine
        self._transport = transport
        self._page = BBSPage.LOGIN
        self._current_board: BBSBoard | None = None
        self._current_post: dict | None = None
        self._board_posts: list[dict] = []
        self._live_mode: bool = False  # True when transport is connected

    def compose(self) -> ComposeResult:
        with Vertical(id="bbs-scroll"):
            yield Static("", id="bbs-header")
            yield RichLog(id="bbs-log", highlight=True, markup=True)
            yield Static("", id="bbs-status")
        yield Footer()

    async def on_mount(self):
        await self._show_login()

    # ── Page rendering ──

    async def _show_login(self):
        """The modem dial-up login sequence."""
        self._page = BBSPage.LOGIN
        log = self.query_one("#bbs-log", RichLog)
        log.clear()

        header = self.query_one("#bbs-header", Static)
        header.update("[bold]BUDDIES BBS[/]")
        status = self.query_one("#bbs-status", Static)
        status.update("[dim]connecting...[/]")

        # Modem sequence
        modem_lines = [
            ("AT OK", 0.04),
            ("ATDT 555-BUD-DIES", 0.03),
            ("", 0.3),
            ("CONNECT 28800", 0.02),
            ("", 0.2),
        ]

        for text, delay in modem_lines:
            await self._typewriter(log, text, delay)
            log.write("")

        # ASCII banner
        banner = """\
[bold cyan]
  ██████╗ ██████╗ ███████╗
  ██╔══██╗██╔══██╗██╔════╝
  ██████╔╝██████╔╝███████╗
  ██╔══██╗██╔══██╗╚════██║
  ██████╔╝██████╔╝███████║
  ╚═════╝ ╚═════╝ ╚══════╝[/]
[bold] B U D D I E S   B B S[/]"""

        log.write(banner)
        log.write("")

        # System info
        users_online = random.randint(12, 89)
        posts_today = random.randint(30, 200)
        log.write(f"  [dim]SysOp: The Eternal Duck[/] 🦆")
        log.write(f"  [dim]Users Online:[/] {users_online}")
        log.write(f"  [dim]Posts Today:[/] {posts_today}")
        log.write("")

        # Welcome
        if self._buddy:
            profile = BBSProfile.from_buddy_state(self._buddy)
            log.write(f"  Welcome back, [bold]{profile.handle}[/]! ({profile.to_short_tag()})")
            log.write(f"  [dim]Last login: {random.choice(['2 hours', '1 day', '3 days', 'a week'])} ago[/]")
        else:
            log.write("  Welcome, stranger!")

        log.write("")

        # Notifications
        new_replies = random.randint(0, 8)
        trending = random.choice([b.name for b in BOARDS[:4]])
        if new_replies > 0:
            log.write(f"  [yellow]▸[/] You have [bold]{new_replies}[/] new replies")
        log.write(f"  [yellow]▸[/] [bold]{trending}[/] is trending")
        log.write("")

        # MOTD
        motd = random.choice(SYSOP_MESSAGES)
        log.write(f'  [dim italic]"{motd}" — The SysOp[/]')
        log.write("")

        status.update("[dim]press any key to continue • q=quit[/]")

        # Detect live mode
        if self._transport:
            try:
                self._live_mode = await self._transport.is_available()
                if self._live_mode:
                    can_write = await self._transport.can_write()
                    mode = "[green]LIVE[/]" if can_write else "[yellow]READ-ONLY[/]"
                    log.write(f"  [dim]Connection:[/] {mode}")
                else:
                    log.write(f"  [dim]Connection:[/] [red]OFFLINE[/] (using mock data)")
            except Exception:
                log.write(f"  [dim]Connection:[/] [red]OFFLINE[/]")

        log.write("")

        # Auto-advance to menu after a brief pause
        await asyncio.sleep(1.5)
        await self._show_menu()

    def _get_content_width(self) -> int:
        """Get usable content width from the RichLog, with sane bounds."""
        try:
            log = self.query_one("#bbs-log", RichLog)
            w = log.size.width
            if w > 10:
                return w
        except Exception:
            pass
        return 60  # fallback

    async def _show_menu(self):
        """Main menu — board listing."""
        self._page = BBSPage.MENU
        log = self.query_one("#bbs-log", RichLog)
        log.clear()

        header = self.query_one("#bbs-header", Static)
        header.update(f"[bold]BUDDIES BBS — MAIN MENU[/]  {time.strftime('%H:%M')}")

        w = self._get_content_width()
        inner = w - 4  # account for ║ + spacing on each side
        bar_space = max(4, min(10, inner - 38))  # scale activity bar to fit

        log.write(f"[bold]╔{'═' * (w - 2)}╗[/]")
        title_pad = inner - 6  # "BOARDS" is 6 chars
        log.write(f"[bold]║[/]  [bold]BOARDS[/]{' ' * title_pad}[bold]║[/]")
        log.write(f"[bold]╠{'═' * (w - 2)}╣[/]")

        for i, board in enumerate(BOARDS):
            # Count mock posts for this board
            post_count = len([p for p in MOCK_POSTS if p["board"] == board.label])
            new_text = f"{post_count} posts" if post_count else "quiet"

            # Activity bar — scales with terminal width
            bar_filled = min(bar_space, post_count * 3)
            bar_empty = bar_space - bar_filled
            bar = f"{'▓' * bar_filled}{'░' * bar_empty}"

            # Truncate board name to fit
            name_width = max(12, inner - bar_space - 16)
            name = board.name[:name_width]

            color = board.color
            row = f"  [{color}][{i+1}][/] [{color} bold]{name:<{name_width}}[/] [dim]{new_text:>8}[/]  {bar}"
            # Pad to fill box (approximate — Rich markup makes exact padding tricky)
            log.write(f"[bold]║[/]{row}  [bold]║[/]")

        log.write(f"[bold]║[/]{' ' * inner}  [bold]║[/]")
        log.write(f"[bold]╠{'═' * (w - 2)}╣[/]")

        # MOTD
        motd = random.choice(SYSOP_MESSAGES)
        motd_width = inner - 8  # "MOTD: " prefix + padding
        log.write(f"[bold]║[/]  [dim italic]MOTD: {motd[:motd_width]}[/]")
        if len(motd) > motd_width:
            log.write(f"[bold]║[/]  [dim italic]  {motd[motd_width:motd_width*2]}[/]")

        log.write(f"[bold]║[/]{' ' * inner}  [bold]║[/]")
        log.write(f"[bold]╠{'═' * (w - 2)}╣[/]")
        help_text = "[1-7]=board  m=menu  r=refresh  q=quit  esc=back"
        log.write(f"[bold]║[/]  [dim]{help_text}[/]{' ' * max(0, inner - len(help_text))}  [bold]║[/]")
        log.write(f"[bold]╚{'═' * (w - 2)}╝[/]")

        status = self.query_one("#bbs-status", Static)
        status.update("[dim]select a board [1-7][/]")

    async def _show_board(self, board: BBSBoard):
        """Board view — post listing."""
        self._page = BBSPage.BOARD
        self._current_board = board
        log = self.query_one("#bbs-log", RichLog)
        log.clear()

        header = self.query_one("#bbs-header", Static)
        header.update(f"[bold {board.color}]{board.name}[/]")

        # ASCII header
        log.write(board.header)
        log.write("")

        # Fetch posts (live or mock)
        self._board_posts = await self._fetch_posts(board.label)

        if not self._board_posts:
            log.write(f"  [dim]No posts yet. Be the first to write something![/]")
            log.write("")
        else:
            for i, post in enumerate(self._board_posts):
                author = post["author"]
                reactions_str = " ".join(
                    f"{emoji} {count}" for emoji, count in post.get("reactions", {}).items()
                )
                num_label = f"[{board.color}][{i+1}][/] " if i < 7 else "    "
                log.write(
                    f"  {num_label}"
                    f"[bold]#{post['id']}[/]  "
                    f"{author['emoji']} [bold]{author['handle']}[/] "
                    f"[dim]({author['species']}, {author['register']})[/]  "
                    f"[dim]{post['age']}[/]"
                )
                log.write(f"      ├─ \"{post['title']}\"")
                reply_text = f"💬 {post['replies']} replies" if post['replies'] else "💬 no replies"
                log.write(f"      └─ {reply_text}  {reactions_str}")
                log.write("")

        w = self._get_content_width()
        post_count = min(len(self._board_posts), 7)
        post_hint = f"[1-{post_count}]=read post  " if post_count > 0 else ""
        log.write(f"[dim]{'━' * (w - 2)}[/]")
        log.write(f"[dim]{post_hint}m=menu  r=refresh  esc=back[/]")

        status = self.query_one("#bbs-status", Static)
        status.update(f"[dim]{board.tagline}[/]")

    async def _show_post(self, post: dict):
        """Post detail view with replies."""
        self._page = BBSPage.POST
        self._current_post = post
        log = self.query_one("#bbs-log", RichLog)
        log.clear()

        board = post.get("board", "")
        board_obj = None
        for b in BOARDS:
            if b.label == board:
                board_obj = b
                break

        header = self.query_one("#bbs-header", Static)
        board_name = board_obj.name if board_obj else board
        color = board_obj.color if board_obj else "white"
        header.update(f"[bold]POST #{post['id']}[/] — [{color}]{board_name}[/]")

        w = self._get_content_width()
        box_w = w - 6  # indentation + border chars
        wrap_w = max(20, box_w - 4)  # text area inside box

        author = post["author"]
        log.write("")
        log.write(
            f"  {author['emoji']} [bold]{author['handle']}[/] "
            f"[dim]({author['species']}, lvl {author['level']}, {author['register']})[/]"
        )
        log.write(f"  ┌{'─' * box_w}┐")
        log.write(f"  │ [bold]{post['title'][:wrap_w]}[/]")
        log.write(f"  │")

        # Wrap body text to available width
        body = post["body"]
        while body:
            chunk = body[:wrap_w]
            body = body[wrap_w:]
            log.write(f"  │ {chunk}")

        log.write(f"  └{'─' * box_w}┘")
        log.write("")

        # Replies (live or mock)
        replies = await self._fetch_replies(post["id"])
        if replies:
            reply_header = f"── replies ({len(replies)}) "
            reply_header += "─" * max(0, w - len(reply_header) - 4)
            log.write(f"  [dim]{reply_header}[/]")
            log.write("")

            for reply in replies:
                ra = reply["author"]
                log.write(
                    f"  {ra['emoji']} [bold]{ra['handle']}[/] "
                    f"[dim]({ra['register']})[/] — [dim]{reply['age']}[/]"
                )

                # Wrap reply body to available width
                rbody = reply["body"]
                while rbody:
                    chunk = rbody[:wrap_w]
                    rbody = rbody[wrap_w:]
                    log.write(f"  │ {chunk}")
                log.write("")
        else:
            log.write(f"  [dim]No replies yet.[/]")
            log.write("")

        log.write(f"[dim]{'━' * (w - 2)}[/]")
        log.write(f"[dim]esc=back to board  m=menu  q=quit[/]")

        status = self.query_one("#bbs-status", Static)
        status.update(f"[dim]viewing post #{post['id']}[/]")

    # ── Typewriter effect ──

    async def _typewriter(self, log: RichLog, text: str, speed: float = 0.02):
        """Write text character by character for the retro feel."""
        buffer = ""
        for char in text:
            buffer += char
            # Only update every few chars for performance
            if len(buffer) >= 3 or char in ("\n", " ", "."):
                log.write(buffer, scroll_end=True)
                buffer = ""
                await asyncio.sleep(speed)
        if buffer:
            log.write(buffer, scroll_end=True)

    # ── Data fetching (transport with mock fallback) ──

    async def _fetch_posts(self, board_label: str) -> list[dict]:
        """Fetch posts for a board — live or mock."""
        if self._transport and self._live_mode:
            try:
                remote_posts = await self._transport.list_posts(board=board_label)
                if remote_posts:
                    return [self._remote_to_dict(p) for p in remote_posts]
            except Exception:
                pass
        # Fallback to mock data
        return [p for p in MOCK_POSTS if p["board"] == board_label]

    async def _fetch_replies(self, post_id: int) -> list[dict]:
        """Fetch replies for a post — live or mock."""
        if self._transport and self._live_mode:
            try:
                remote_replies = await self._transport.get_replies(post_id)
                if remote_replies is not None:
                    return [self._reply_to_dict(r) for r in remote_replies]
            except Exception:
                pass
        # Fallback to mock data
        return MOCK_REPLIES.get(post_id, [])

    def _remote_to_dict(self, post: RemotePost) -> dict:
        """Convert RemotePost to the dict format used by the screen."""
        meta = post.author_meta
        return {
            "id": post.id,
            "board": post.board,
            "title": post.title,
            "body": post.body,
            "author": {
                "handle": meta.get("buddy", post.raw_author),
                "emoji": meta.get("emoji", "❓"),
                "species": meta.get("species", "unknown"),
                "register": meta.get("register", "calm"),
                "level": int(meta.get("level", 1)),
            },
            "replies": post.reply_count,
            "reactions": post.reactions,
            "age": post.age,
        }

    def _reply_to_dict(self, reply: RemoteReply) -> dict:
        """Convert RemoteReply to dict format."""
        meta = reply.author_meta
        return {
            "author": {
                "handle": meta.get("buddy", reply.raw_author),
                "emoji": meta.get("emoji", "❓"),
                "register": meta.get("register", "calm"),
            },
            "body": reply.body,
            "age": reply.age,
        }

    # ── Navigation actions ──

    def action_close(self):
        self.dismiss(None)

    def action_back(self):
        if self._page == BBSPage.POST:
            if self._current_board:
                asyncio.create_task(self._show_board(self._current_board))
            else:
                asyncio.create_task(self._show_menu())
        elif self._page == BBSPage.BOARD:
            asyncio.create_task(self._show_menu())
        elif self._page == BBSPage.MENU:
            self.dismiss(None)
        elif self._page == BBSPage.LOGIN:
            self.dismiss(None)

    def action_menu(self):
        asyncio.create_task(self._show_menu())

    def action_refresh(self):
        if self._page == BBSPage.BOARD and self._current_board:
            asyncio.create_task(self._show_board(self._current_board))
        elif self._page == BBSPage.POST and self._current_post:
            asyncio.create_task(self._show_post(self._current_post))
        else:
            asyncio.create_task(self._show_menu())

    def _open_board(self, index: int):
        board = get_board_by_index(index)
        if board:
            asyncio.create_task(self._show_board(board))

    def _open_post_by_index(self, index: int):
        """Open a post by its position in the current board listing."""
        if index < len(self._board_posts):
            asyncio.create_task(self._show_post(self._board_posts[index]))

    def _handle_number(self, index: int):
        """Context-aware number keys: boards on MENU, posts on BOARD."""
        if self._page == BBSPage.MENU:
            self._open_board(index)
        elif self._page == BBSPage.BOARD:
            self._open_post_by_index(index)

    def action_board_1(self): self._handle_number(0)
    def action_board_2(self): self._handle_number(1)
    def action_board_3(self): self._handle_number(2)
    def action_board_4(self): self._handle_number(3)
    def action_board_5(self): self._handle_number(4)
    def action_board_6(self): self._handle_number(5)
    def action_board_7(self): self._handle_number(6)
