"""Trivia game engine — coding/tech multiple choice questions.

The buddy also answers each question. Its personality determines how
it picks: high-DEBUGGING = often correct, high-CHAOS = random,
high-WISDOM = correct on theory, high-SNARK = snarky commentary.
Buddy answers are revealed after the player picks.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from buddies.core.buddy_brain import BuddyState
from buddies.core.games import GameType, GameOutcome, GameResult
from buddies.core.games.engine import GamePersonality, personality_from_state


@dataclass
class Question:
    """A trivia question."""
    text: str
    choices: list[str]    # 4 choices, A-D
    answer: int           # Index of correct answer (0-3)
    category: str         # "basics", "history", "bugs", "culture", "languages"
    difficulty: int       # 1=easy, 2=medium, 3=hard

    @property
    def correct_letter(self) -> str:
        return chr(65 + self.answer)  # A, B, C, D


# ---------------------------------------------------------------------------
# Question bank — 100+ coding/tech trivia questions
# ---------------------------------------------------------------------------

QUESTIONS: list[Question] = [
    # === BASICS (easy) ===
    Question("What does HTML stand for?",
             ["Hyper Text Markup Language", "High Tech Modern Language",
              "Home Tool Markup Language", "Hyperlink Text Making Language"],
             0, "basics", 1),
    Question("What symbol starts a comment in Python?",
             ["//", "#", "/*", "--"],
             1, "basics", 1),
    Question("What does CSS stand for?",
             ["Computer Style Sheets", "Cascading Style Sheets",
              "Creative Style System", "Colorful Style Sheets"],
             1, "basics", 1),
    Question("Which of these is NOT a programming language?",
             ["Rust", "Go", "HTML", "Java"],
             2, "basics", 1),
    Question("What does CPU stand for?",
             ["Central Processing Unit", "Computer Personal Unit",
              "Central Program Utility", "Core Processing Unit"],
             0, "basics", 1),
    Question("How many bits are in a byte?",
             ["4", "8", "16", "32"],
             1, "basics", 1),
    Question("What does 'git push' do?",
             ["Downloads changes", "Uploads local commits to remote",
              "Creates a new branch", "Deletes a file"],
             1, "basics", 1),
    Question("What is the value of True + True in Python?",
             ["True", "2", "TrueTrue", "Error"],
             1, "basics", 1),
    Question("What data structure uses FIFO (First In, First Out)?",
             ["Stack", "Queue", "Tree", "Graph"],
             1, "basics", 1),
    Question("What does API stand for?",
             ["Application Programming Interface", "Advanced Program Integration",
              "Automated Processing Input", "Application Process Interaction"],
             0, "basics", 1),

    # === HISTORY (medium) ===
    Question("Who is considered the father of computer science?",
             ["Bill Gates", "Alan Turing", "Steve Jobs", "Dennis Ritchie"],
             1, "history", 2),
    Question("What year was Python first released?",
             ["1989", "1991", "1995", "2000"],
             1, "history", 2),
    Question("Who created Linux?",
             ["Richard Stallman", "Dennis Ritchie", "Linus Torvalds", "Ken Thompson"],
             2, "history", 2),
    Question("What was the first high-level programming language?",
             ["COBOL", "Fortran", "BASIC", "C"],
             1, "history", 2),
    Question("What company created JavaScript?",
             ["Microsoft", "Sun Microsystems", "Netscape", "Google"],
             2, "history", 2),
    Question("What year was the first iPhone released?",
             ["2005", "2006", "2007", "2008"],
             2, "history", 2),
    Question("Who invented the World Wide Web?",
             ["Vint Cerf", "Tim Berners-Lee", "Marc Andreessen", "Robert Cailliau"],
             1, "history", 2),
    Question("What does the 'C' in C++ stand for?",
             ["Computer", "It's the language C, incremented", "Code", "Compiled"],
             1, "history", 2),
    Question("What was the first computer virus called?",
             ["ILOVEYOU", "Creeper", "Melissa", "MyDoom"],
             1, "history", 2),
    Question("What language was originally called 'Oak'?",
             ["JavaScript", "Java", "Ruby", "Swift"],
             1, "history", 2),

    # === BUGS & DEBUGGING (medium) ===
    Question("What is a 'segfault'?",
             ["A typo in code", "An access to invalid memory",
              "A network timeout", "A missing file"],
             1, "bugs", 2),
    Question("What HTTP status code means 'Not Found'?",
             ["403", "404", "500", "301"],
             1, "bugs", 2),
    Question("What is a 'race condition'?",
             ["When code runs too fast", "When two processes compete for the same resource",
              "When a loop never ends", "When memory runs out"],
             1, "bugs", 2),
    Question("What does a 'stack overflow' literally mean?",
             ["Too much data on the heap", "The call stack exceeded its limit",
              "The CPU overheated", "Too many global variables"],
             1, "bugs", 2),
    Question("What's the term for code that works but nobody knows why?",
             ["Spaghetti code", "Legacy code", "Magic code", "Haunted code"],
             2, "bugs", 2),
    Question("What is 'rubber duck debugging'?",
             ["Using a rubber duck USB device", "Explaining code out loud to find bugs",
              "A Python testing framework", "Debugging in a bathtub"],
             1, "bugs", 2),
    Question("What does 'NaN' stand for?",
             ["No Answer Needed", "Not a Number", "New Allocation Null", "Next Available Node"],
             1, "bugs", 2),
    Question("What's a 'heisenbug'?",
             ["A bug in quantum computing", "A bug that changes when you try to observe it",
              "A German programming error", "A bug in the Heisenberg compiler"],
             1, "bugs", 2),
    Question("What HTTP status code means 'I'm a Teapot'?",
             ["404", "418", "420", "451"],
             1, "bugs", 2),
    Question("What is a 'memory leak'?",
             ["RAM physically leaking", "Allocated memory that is never freed",
              "Data being sent over the network", "A broken cache"],
             1, "bugs", 2),

    # === CULTURE (mixed difficulty) ===
    Question("What does 'sudo' stand for in Linux?",
             ["Super User Do", "System Utility Device Operation",
              "Secure Undo", "Sub-Directory Utility"],
             0, "culture", 1),
    Question("What is the answer to life, the universe, and everything (per Hitchhiker's Guide)?",
             ["0", "42", "100", "π"],
             1, "culture", 1),
    Question("What animal is the Python language named after?",
             ["A snake", "Monty Python (comedy group)", "A mythical python", "Nothing — it's an acronym"],
             1, "culture", 2),
    Question("What does 'RTFM' stand for?",
             ["Read The Fine Manual", "Run The Full Module",
              "Return To Factory Mode", "Real-Time File Manager"],
             0, "culture", 1),
    Question("In Unix, what does the command 'rm -rf /' do?",
             ["Restores files", "Recursively deletes everything from root",
              "Renames all files", "Resets the machine"],
             1, "culture", 2),
    Question("What is 'localhost'?",
             ["A web hosting company", "Your own computer (127.0.0.1)",
              "The nearest server", "A default website"],
             1, "culture", 1),
    Question("What programming language was named after a coffee?",
             ["Go", "Java", "Mocha", "Espresso"],
             1, "culture", 1),
    Question("What does 'LGTM' mean in code review?",
             ["Let's Go To Meeting", "Looks Good To Me",
              "Last Git Tag Merged", "Load General Test Module"],
             1, "culture", 1),
    Question("What is the 'bus factor' of a project?",
             ["How many buses use its API", "Number of people who could be hit by a bus before the project dies",
              "The speed of the project bus", "A measure of project size"],
             1, "culture", 2),
    Question("What color is the screen of death on Windows?",
             ["Red", "Green", "Blue", "Black"],
             2, "culture", 1),

    # === LANGUAGES (hard) ===
    Question("Which language uses 'fn' to declare functions?",
             ["Go", "Rust", "Kotlin", "Swift"],
             1, "languages", 3),
    Question("What is Haskell primarily known for?",
             ["Object-oriented programming", "Pure functional programming",
              "Systems programming", "Web development"],
             1, "languages", 3),
    Question("Which language uses 'val' and 'var' for declarations?",
             ["Python", "JavaScript", "Kotlin", "C#"],
             2, "languages", 2),
    Question("What language powers most Arduino programs?",
             ["Python", "Java", "C/C++", "Rust"],
             2, "languages", 2),
    Question("Which language has a mascot called 'Gopher'?",
             ["Rust", "Go", "Elixir", "Perl"],
             1, "languages", 2),
    Question("What is TypeScript's relationship to JavaScript?",
             ["Completely different language", "A superset with static types",
              "A subset with fewer features", "A compiled version"],
             1, "languages", 2),
    Question("Which language uses indentation for code blocks (no braces)?",
             ["Ruby", "Python", "Go", "Rust"],
             1, "languages", 1),
    Question("What language was originally designed for iOS development?",
             ["Kotlin", "Dart", "Swift", "Objective-C"],
             2, "languages", 2),
    Question("Which language's package manager is called 'cargo'?",
             ["Go", "Rust", "Ruby", "Elixir"],
             1, "languages", 2),
    Question("What does SQL stand for?",
             ["Simple Query Language", "Structured Query Language",
              "System Query Logic", "Sequential Query Language"],
             1, "languages", 1),

    # === ADVANCED (hard) ===
    Question("What is Big O notation used for?",
             ["Measuring code beauty", "Describing algorithm complexity",
              "Counting lines of code", "Rating developer skill"],
             1, "basics", 2),
    Question("What sorting algorithm has worst-case O(n²) but is often fastest in practice?",
             ["Merge Sort", "Bubble Sort", "Quicksort", "Insertion Sort"],
             2, "basics", 3),
    Question("What does SOLID stand for in software design?",
             ["5 design principles", "A type of architecture",
              "A testing framework", "A database pattern"],
             0, "basics", 2),
    Question("What is a 'closure' in programming?",
             ["Shutting down a program", "A function that captures its environment",
              "A type of loop", "End of a code block"],
             1, "languages", 3),
    Question("What does REST stand for?",
             ["Real-time Event Streaming Technology",
              "Representational State Transfer",
              "Remote Execution Server Tool",
              "Reliable Service Transport"],
             1, "basics", 2),
    Question("In Git, what does 'rebase' do?",
             ["Creates a new repository", "Moves commits to a new base commit",
              "Deletes old branches", "Backs up the database"],
             1, "basics", 3),
    Question("What is 'monkey patching'?",
             ["Fixing code with duct tape", "Dynamically modifying code at runtime",
              "A testing technique", "Writing code for monkeys"],
             1, "languages", 3),
    Question("What design pattern is a 'singleton'?",
             ["A pattern that creates multiple instances",
              "A pattern ensuring only one instance exists",
              "A pattern for single-threaded apps",
              "A pattern for single-page apps"],
             1, "basics", 2),
    Question("What does 'CORS' stand for?",
             ["Cross-Origin Resource Sharing",
              "Central Object Response System",
              "Client-Oriented Request Service",
              "Cross-Origin Request Security"],
             0, "bugs", 3),
    Question("What is 'technical debt'?",
             ["Money owed for tech equipment",
              "The cost of rework caused by choosing quick solutions",
              "Unpaid software licenses",
              "The time spent learning new tech"],
             1, "culture", 2),

    # === BONUS WEIRD ONES ===
    Question("What is the output of '[] + []' in JavaScript?",
             ["[]", "0", "'' (empty string)", "undefined"],
             2, "languages", 3),
    Question("In Python, what is the output of 0.1 + 0.2?",
             ["0.3", "0.30000000000000004", "0.2999999", "Error"],
             1, "languages", 2),
    Question("What is the maximum value of a signed 32-bit integer?",
             ["2,147,483,647", "4,294,967,295", "32,767", "65,535"],
             0, "basics", 3),
    Question("What emoji represents a 'bug' in most dev tools?",
             ["🐛", "🪲", "🐜", "🦗"],
             0, "culture", 1),
    Question("What year did Stack Overflow launch?",
             ["2006", "2008", "2010", "2012"],
             1, "history", 3),
    Question("Who created the Rust programming language?",
             ["Google", "Mozilla", "Microsoft", "Apple"],
             1, "history", 3),
    Question("What does 'YAGNI' stand for?",
             ["You Aren't Gonna Need It", "Yet Another GNU Notation Interface",
              "Your Application's Got No Issues", "You Already Got New Ideas"],
             0, "culture", 2),
    Question("What is the 'halting problem'?",
             ["When a computer stops unexpectedly",
              "Determining if a program will ever finish running",
              "A bug in infinite loops",
              "When the CPU overheats and halts"],
             1, "basics", 3),
    Question("What does the 'D' in CRUD stand for?",
             ["Deploy", "Debug", "Delete", "Download"],
             2, "basics", 1),
    Question("In hexadecimal, what does 0xFF equal in decimal?",
             ["255", "256", "128", "512"],
             0, "basics", 2),
    Question("What is 'XSS' in web security?",
             ["Extra Secure System", "Cross-Site Scripting",
              "XML Style Sheet", "Extended Server Security"],
             1, "bugs", 3),
    Question("What is a 'docker container'?",
             ["A physical server rack", "A lightweight isolated runtime environment",
              "A type of database", "A network switch"],
             1, "basics", 2),
    Question("What does JSON stand for?",
             ["Java Standard Object Notation", "JavaScript Object Notation",
              "JSON Serialized Object Network", "Just Simple Object Naming"],
             1, "basics", 1),
    Question("What is the Fibonacci sequence's first 6 numbers?",
             ["1,1,2,3,5,8", "0,1,1,2,3,5", "1,2,3,5,8,13", "0,1,2,3,5,8"],
             1, "basics", 2),
    Question("Who created Git?",
             ["Bill Gates", "Linus Torvalds", "Guido van Rossum", "James Gosling"],
             1, "history", 2),
    Question("What's the keyboard shortcut to undo in most editors?",
             ["Ctrl+Z", "Ctrl+U", "Ctrl+R", "Ctrl+X"],
             0, "basics", 1),
    Question("What is 'localhost:3000' commonly used for?",
             ["A game server", "Local development web server",
              "Email client", "File sharing"],
             1, "culture", 1),
    Question("What is a 'pull request'?",
             ["Downloading a file", "Requesting to merge code changes",
              "Pulling data from an API", "A request to delete code"],
             1, "basics", 1),
    Question("What language is known for 'There's more than one way to do it'?",
             ["Python", "Perl", "Ruby", "PHP"],
             1, "languages", 3),
    Question("What is the time complexity of binary search?",
             ["O(n)", "O(log n)", "O(n²)", "O(1)"],
             1, "basics", 2),
    Question("Which company developed the Go programming language?",
             ["Facebook", "Amazon", "Google", "Microsoft"],
             2, "languages", 2),
    Question("What does 'MVP' stand for in software development?",
             ["Most Valuable Programmer", "Minimum Viable Product",
              "Master Version Protocol", "Main Virtual Process"],
             1, "culture", 1),
    Question("What does 'chmod 777' do on Unix?",
             ["Deletes all files", "Gives everyone full read/write/execute permissions",
              "Changes the owner", "Encrypts the file"],
             1, "culture", 3),
    Question("What is 'vim' primarily known for?",
             ["A web browser", "A text editor that's hard to exit",
              "A package manager", "A testing framework"],
             1, "culture", 1),
    Question("What does 'refactoring' mean?",
             ["Adding new features", "Restructuring code without changing its behavior",
              "Fixing bugs", "Deleting old code"],
             1, "basics", 1),
    Question("What is WebAssembly (WASM)?",
             ["A JavaScript framework", "A binary instruction format for the web",
              "A CSS preprocessor", "An HTML extension"],
             1, "languages", 3),
    Question("What year was GitHub founded?",
             ["2005", "2008", "2010", "2012"],
             1, "history", 3),
    Question("What does 'DRY' stand for in programming?",
             ["Do Repeat Yourself", "Don't Repeat Yourself",
              "Develop, Review, Yield", "Debug Runtime Yields"],
             1, "culture", 1),
    Question("What is 'Kubernetes' named after?",
             ["A Greek word for helmsman", "A Star Trek character",
              "A type of container ship", "The inventor's cat"],
             0, "culture", 3),
    Question("How do you exit vim?",
             ["Ctrl+C", ":q!", "Alt+F4", "Esc then :exit"],
             1, "culture", 1),
]

QUESTIONS_PER_ROUND = 10


@dataclass
class TriviaRound:
    """A single trivia question round result."""
    question: Question
    player_answer: int       # 0-3 index
    buddy_answer: int        # 0-3 index
    player_correct: bool
    buddy_correct: bool


@dataclass
class TriviaGame:
    """A full trivia game — 10 questions, player and buddy both answer."""
    buddy_state: BuddyState
    personality: GamePersonality = field(init=False)

    questions: list[Question] = field(default_factory=list)
    rounds: list[TriviaRound] = field(default_factory=list)
    current_index: int = 0
    player_score: int = 0
    buddy_score: int = 0
    is_over: bool = False

    def __post_init__(self):
        self.personality = personality_from_state(self.buddy_state)
        self._pick_questions()

    def _pick_questions(self):
        """Pick a balanced set of questions across categories and difficulties."""
        pool = list(QUESTIONS)
        random.shuffle(pool)

        # Try to get a mix of difficulties
        easy = [q for q in pool if q.difficulty == 1]
        medium = [q for q in pool if q.difficulty == 2]
        hard = [q for q in pool if q.difficulty == 3]

        selected: list[Question] = []
        # 3 easy, 4 medium, 3 hard
        selected.extend(easy[:3])
        selected.extend(medium[:4])
        selected.extend(hard[:3])

        # Fill remaining from whatever's available
        while len(selected) < QUESTIONS_PER_ROUND:
            remaining = [q for q in pool if q not in selected]
            if not remaining:
                break
            selected.append(remaining[0])

        random.shuffle(selected)
        self.questions = selected[:QUESTIONS_PER_ROUND]

    @property
    def current_question(self) -> Question | None:
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def get_buddy_answer(self, question: Question) -> int:
        """Determine what the buddy would answer based on personality.

        High debugging/wisdom = more likely correct.
        High chaos = more random.
        """
        correct = question.answer

        # Base chance of being correct scales with optimal_play
        # Also factor in difficulty
        difficulty_penalty = {1: 0.0, 2: 0.15, 3: 0.3}[question.difficulty]
        correct_chance = self.personality.optimal_play - difficulty_penalty

        if random.random() < correct_chance:
            return correct

        # Otherwise pick a wrong answer
        # High chaos = truly random wrong answer
        # Otherwise slightly biased toward adjacent answers
        wrong = [i for i in range(4) if i != correct]
        return random.choice(wrong)

    def answer(self, player_choice: int) -> TriviaRound:
        """Player answers the current question. Returns the round result."""
        q = self.current_question
        if q is None:
            raise ValueError("No more questions")

        buddy_choice = self.get_buddy_answer(q)

        player_correct = player_choice == q.answer
        buddy_correct = buddy_choice == q.answer

        if player_correct:
            self.player_score += 1
        if buddy_correct:
            self.buddy_score += 1

        rnd = TriviaRound(
            question=q,
            player_answer=player_choice,
            buddy_answer=buddy_choice,
            player_correct=player_correct,
            buddy_correct=buddy_correct,
        )
        self.rounds.append(rnd)

        self.current_index += 1
        if self.current_index >= len(self.questions):
            self.is_over = True

        return rnd

    def get_result(self) -> GameResult:
        """Build a GameResult from the completed game."""
        if self.player_score > self.buddy_score:
            outcome = GameOutcome.WIN
            xp = 20 + self.player_score * 2  # Bonus per correct answer
            mood = 5
        elif self.player_score < self.buddy_score:
            outcome = GameOutcome.LOSE
            xp = 5 + self.player_score * 2
            mood = -2
        else:
            outcome = GameOutcome.DRAW
            xp = 10 + self.player_score * 2
            mood = 0

        return GameResult(
            game_type=GameType.TRIVIA,
            outcome=outcome,
            buddy_id=0,
            score={"player": self.player_score, "buddy": self.buddy_score,
                   "total": len(self.questions),
                   "perfect": self.player_score == len(self.questions)},
            xp_earned=xp,
            mood_delta=mood,
        )
