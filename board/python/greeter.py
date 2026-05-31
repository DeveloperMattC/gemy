#!/usr/bin/env python3
"""Gemy — the Coralboard greeting robot. Beeps back (and flashes LEDs) when it
sees you wave, sees a hand held up, hears its name ("Gemy"), or speaks to it
on the HAT microphone.

Run on the board with the venv python (OpenCV + sounddevice + Moonshine):

  /home/root/sl2610-examples/.venv/bin/python3 /home/root/greeter.py
  ... greeter.py --no-speech            # vision only (wave + hand-up)
  ... greeter.py --no-vision            # ears only ("hello"/"hi")
  ... greeter.py --sensitivity high --gain 600
  ... greeter.py --audio-device 0       # pick the HAT mic explicitly

Ctrl+C to stop. Buzzer/LED/camera are always released on exit.
"""
import argparse
import collections
import os
import re
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/root/sl2610-examples")   # for utils.speech
import hat

try:
    import gemy_diag
except ImportError:
    gemy_diag = None  # type: ignore
try:
    import gemy_trace
except ImportError:
    gemy_trace = None  # type: ignore

try:
    import gemy_stability as _stability
except ImportError:
    _stability = None  # type: ignore

import gemy_classify
import gemy_empathy
import gemy_fallback
import gemy_math
import gemy_phrase_buffer
import gemy_qa
import gemy_reactions

# Inviolable: buzzer/LED never on > hat.MAX_OUTPUT_ON_SEC (see .cursor/rules/gemy-hardware-safety.mdc)
hat.start_safety_watchdog()


def _diag(phase: str, detail: str = "") -> None:
    if gemy_diag is not None:
        gemy_diag.log(phase, detail)


def _trace(event: str, detail: str = "") -> None:
    if gemy_trace is not None:
        gemy_trace.trace(event, detail)


def _diag_phase(phase: str, detail: str = "") -> None:
    if gemy_trace is not None:
        gemy_trace.set_phase(phase, detail)
    if gemy_diag is not None:
        gemy_diag.set_phase(phase, detail)


def _stop_stale_demos():
    """Kill leftover greeter or old demos holding camera/mic."""
    import subprocess
    me = str(os.getpid())
    try:
        out = subprocess.check_output(["ps", "-ef"], text=True, errors="replace")
    except Exception:
        return
    killed = []
    for line in out.splitlines():
        if "wave_detect.py" not in line and "greeter.py" not in line:
            continue
        if "grep" in line:
            continue
        parts = line.split()
        if len(parts) < 2 or not parts[1].isdigit():
            continue
        pid = parts[1]
        if pid == me:
            continue
        try:
            os.kill(int(pid), 9)
            killed.append(pid)
        except OSError:
            pass
    if killed:
        print(f"[startup] stopped old demo PID(s): {', '.join(killed)}")
        time.sleep(1.0)


# ---- reactions: light + sound personalities --------------------------------
def _concurrent(*fns):
    """Run the given no-arg callables at the same time and wait for all."""
    ts = [threading.Thread(target=f, daemon=True) for f in fns]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def _react_gemy():
    hat.gemy_name_ack()


def _react_greet():
    hat.gemy_greet()


def _react_funny():
    hat.gemy_funny()


def _react_nice():
    hat.gemy_nice()


def _react_mean():
    hat.gemy_mean()


def _react_sad():
    hat.gemy_sad()


def _react_neutral():
    hat.gemy_neutral()


def _react_yes():
    hat.gemy_yes()


def _react_no():
    hat.gemy_no()


# Heard-name triggers (Moonshine may spell slightly wrong)
GEMY_NAMES = {"gemy", "gemi", "jemmy", "jimmy"}
_GREETING_WORDS = frozenset({"hi", "hey", "hello", "hiya", "yo", "howdy"})


def _is_greeting_with_name(low: str, words: set) -> bool:
    """'hi gemy' / 'hello Gemy' — fast path before math/QA/Gemma."""
    if not (words & GEMY_NAMES or "gemy" in low or "gemi" in low):
        return False
    return bool(words & _GREETING_WORDS) or any(
        p in low for p in ("hi ", "hey ", "hello ", "hiya ", "howdy ")
    )

REACTIONS = {
    "gemy":      _react_gemy,
    "greet":     _react_greet,
    "funny":     _react_funny,
    "nice":      _react_nice,
    "mean":      _react_mean,
    "sad":       _react_sad,
    "yes":       _react_yes,
    "no":        _react_no,
    "neutral":   _react_neutral,
}

_missing_reactions = gemy_reactions.BEEP_REACTIONS - frozenset(REACTIONS)
if _missing_reactions:
    raise RuntimeError(
        f"greeter.REACTIONS missing beep moods: {sorted(_missing_reactions)} "
        "(classify can return a kind with no handler — see test_gemy_wiring.py)"
    )

_LABELS = {
    "gemy":           "Hi, I'm Gemy!",
    "greet":          "Hi!",
    "funny":          "haha, good one!",
    "nice":           "yay, thank you!!",
    "mean":           "...hey, that's mean",
    "sad":            "*sniff* that makes me sad...",
    "yes":            "yes!",
    "no":             "nope.",
    "neutral":        "hmm, ok",
}

# ---- sentiment / intent of what was heard ----------------------------------
FUNNY = {"haha", "hahaha", "lol", "lmao", "rofl", "hehe", "heh", "hilarious",
         "funny", "joke", "jokes", "joking", "kidding", "punchline", "rimshot",
         "comedian", "comedie", "comedy", "humor", "humour", "laugh", "laughing",
         "giggle", "chuckle", "silly", "goofy", "witty"}
# Knock-knock payoffs and classic punchline fragments (Moonshine may garble spelling).
_JOKE_PUNCHLINE_FRAGMENTS = (
    "orange you", "oranges you", "lettuce in", "lettuce n", "let us in",
    "cow go", "udder", "boo who", "ice cream", "nobel", "no bell",
    "honeydew", "honey do", "cantelope", "cantaloupe", "pan ts", "pants",
    "atch", "atchoo", "broken pencil", "little old lady", "adore",
    "anya", "rhino", "tank", "figs", "water you", "dishes", "kenya",
    "justin", "olive", "eww", "ewe", "ammunition", "america", "banana split",
    "orange are", "got a", "get it", "got it",
    "longer sandwich", "see through", "call him", "call her",
)
# Riddle / one-liner setups (substring match on normalized text).
_JOKE_SETUP_PHRASES = (
    "why did", "why do", "why does", "why would", "why is the", "why are the",
    "what do you call", "what did the", "what does a", "what do you get",
    "how do you make", "how does a", "how do you catch",
    "knock knock", "knockknock", "noc noc", "nock nock",
    "a man walks into", "a guy walks into", "so this guy", "there once was",
    "want to hear a joke", "hear a joke", "tell you a joke", "heres a joke",
    "here is a joke", "i have a joke", "got a joke",
)
# Strong punchlines for riddles (not bare "because" — too many false positives).
_JOKE_PAYOFF_PHRASES = (
    "to get to", "to reach the", "the other side", "other side",
    "so he could", "so she could", "so it could",
    "call him", "call her", "call it", "didnt say banana", "didn't say banana",
    "orange you glad", "lettuce in", "cow go", "ba dum", "rimshot",
)
NICE = {"good", "great", "nice", "love", "lovely", "awesome", "amazing",
        "wonderful", "cute", "sweet", "smart", "clever", "thanks", "thank",
        "pretty", "beautiful", "cool", "best", "wow", "adorable", "brilliant",
        "fantastic", "excellent", "perfect", "proud", "helpful", "friendly",
        "kind", "gentle", "marvelous", "super", "yay", "hurray", "hooray"}
MEAN = {
    "stupid", "dumb", "hate", "hated", "hates", "hating", "idiot", "moron",
    "ugly", "useless", "terrible", "awful", "suck", "sucks", "sucky", "sucked",
    "annoying", "worst", "bad", "shut", "lame", "garbage", "trash", "mean",
    "rude", "nasty", "cruel", "pathetic", "worthless", "horrible", "jerk",
    "jerks", "fool", "loser", "dumbest", "stinks", "stink", "shutup",
    "dislike", "insult", "insults", "yuck", "gross", "poop", "butt",
    "disgusting", "vile", "heck", "darn", "sucks", "boring", "weak",
}
# Phrases Moonshine often hears (substring match on normalized text).
YES = {"yes", "yeah", "yep", "yup", "yah", "ya", "sure", "absolutely",
       "correct", "affirmative", "ok", "okay", "indeed", "certainly",
       "definitely", "right", "true", "aye", "agreed", "agree"}
NO = {"no", "nope", "nah", "nuh", "negative", "incorrect", "wrong",
      "never", "nix", "false", "deny", "refuse"}
_YES_PHRASES = (
    "of course", "for sure", "you bet", "thats right", "that's right",
    "sounds good", "yes please", "i agree", "i do agree", "sure thing",
    "why yes", "oh yes", "yes i am", "yes we are", "definitely yes",
    "uh huh", "uh-huh", "mm hmm", "mm-hmm",
)
_NO_PHRASES = (
    "no way", "not really", "i disagree", "dont think so", "do not think so",
    "absolutely not", "definitely not", "no thank you", "no thanks",
    "not at all", "of course not", "heck no", "nah nah",
)

_MEAN_PHRASES = (
    "shut up", "shut your", "shut the", "go away", "get lost", "get out",
    "hate you", "hate u", "i hate", "you suck", "you stink", "so dumb",
    "so stupid", "you idiot", "you moron", "you jerk", "you ugly",
    "youre stupid", "youre dumb", "youre ugly", "youre the worst",
    "your stupid", "your dumb", "your ugly", "your the worst",
    "stupid robot", "dumb robot", "hate robot", "worst robot", "bad robot",
    "ugly robot", "shut up robot", "dont like you", "do not like you",
    "not cool", "youre mean", "you are mean", "thats mean", "that mean",
    "piece of junk", "piece of trash", "leave me alone",
)
# Emotional hurt, loss, loneliness — cry (blue), not insult anger (red).
SAD = {
    "sad", "sadness", "saddened", "unhappy", "upset", "miserable", "depressed",
    "depressing", "lonely", "loneliness", "alone", "crying", "cries", "cried",
    "tears", "tearful", "hurt", "hurts", "hurting", "heartbroken", "devastated",
    "gloomy", "mourn", "mourning", "tragic", "tragedy", "grief", "grieving",
    "sob", "sobbing", "whimper", "abandon", "abandoned", "rejected", "rejection",
    "ignored", "forgotten", "leaving", "farewell", "pity", "died", "dead", "death",
    "funeral", "sick", "illness", "hospital", "cry", "weep", "sniff",
    "regret", "miss", "missing", "failed", "failure", "lost",
}
_SAD_PHRASES = (
    "feel sad", "so sad", "thats sad", "that sad", "how sad", "makes me sad",
    "make me sad", "im sad", "i am sad", "feel so bad", "feel bad",
    "bad news", "sad news", "terrible news", "awful news",
    "no one likes you", "nobody likes you", "no one loves you", "nobody loves you",
    "nobody wants you", "no one wants you", "nobody cares", "no one cares",
    "all alone", "so lonely", "leave you", "leaving you", "left you", "going away",
    "dont want you", "do not want you", "won't play with you", "wont play with you",
    "new robot", "replace you", "replacing you", "throw you away", "throwing you away",
    "feel sorry for you", "poor gemy", "poor little gemy", "must be lonely",
    "you must be sad", "are you sad", "made me cry", "made me sad",
    "im crying", "i am crying", "boo hoo", "sniff sniff",
    "dog died", "cat died", "pet died", "someone died", "your friend died",
    "everyone left", "nobody wants", "no friends", "without friends",
    "say goodbye", "saying goodbye", "goodbye forever", "goodbye gemy",
    "dont need you", "do not need you", "getting rid of you",
    "i miss you", "miss you gemy", "feel guilty", "my fault",
)
_NICE_PHRASES = (
    "thank you", "thanks gemy", "love you", "love you gemy", "you rock",
    "you rule", "well done", "good job", "nice job", "so cool",
    "you're the best", "youre the best", "you are the best",
    "great to hear", "good to hear", "nice to hear", "glad to hear",
    "happy to hear", "wonderful to hear", "love to hear",
    "sounds great", "sounds good", "thats great", "that's great",
    "thats good", "that's good", "good to know",
)
_CONVERSATION_GREET = (
    "how are you", "how are you doing", "how are you today", "how are ya",
    "hows it going", "how is it going", "how have you been", "how you doing",
    "whats up", "what's up", "what is up", "nice to meet", "pleased to meet",
    "good to see you", "good to see ya", "hope you are well", "hope youre well",
    "can i see", "can you see", "can you look", "look at me", "show me",
)
# News / feelings that use "bad" or "terrible" but are not insults.
_SAD_NOT_MEAN_PHRASES = (
    "bad news", "sad news", "terrible news", "awful news", "thats too bad",
    "that's too bad", "feel sorry", "poor gemy",
)


def _norm_heard(low):
    """Collapse punctuation so knock-knock / who's there match reliably."""
    return low.replace("-", " ").replace("'", "")


def _words_from_text(text):
    """Tokenize for keyword matching; forgiving for Moonshine output."""
    low = _norm_heard(text.lower())
    words = set()
    for piece in re.findall(r"[a-z0-9]+", low):
        if piece:
            words.add(piece)
    return low, words


def _is_yes(low, words):
    if words & NO:
        return False
    # Do not treat quiz words ("correct", "right") as agreement during a question.
    if gemy_qa.looks_like_question(low):
        if any(p in low for p in _YES_PHRASES):
            return True
        if low.strip() in ("y", "ya", "yea"):
            return True
        return False
    if words & YES:
        return True
    if any(p in low for p in _YES_PHRASES):
        return True
    if low.strip() in ("y", "ya", "yea"):
        return True
    return False


def _is_no(low, words):
    if words & YES and not (words & NO):
        return False
    if gemy_qa.looks_like_question(low):
        if any(p in low for p in _NO_PHRASES):
            return True
        return False
    if words & NO:
        return True
    if any(p in low for p in _NO_PHRASES):
        return True
    if " no " in f" {low} " or low.startswith("no ") or low.endswith(" no"):
        return True
    return False


_OFF_PHRASES = (
    "turn off", "turnoff", "power off", "power down", "shut down", "shutdown",
    "go to sleep", "sleep now", "stop now", "stop listening", "be quiet",
    "quiet down", "good night", "goodnight", "gemy off", "gemi off",
)

def wants_turn_off(low, words, text):
    """Voice command to stop Gemy (checked before mood reactions)."""
    if any(p in low for p in _OFF_PHRASES):
        return True
    if "off" in words and (words & GEMY_NAMES or "gemy" in low or "turn" in words):
        return True
    if "stop" in words and (words & GEMY_NAMES or "gemy" in low):
        return True
    if (words & {"goodbye", "bye"}) and (words & GEMY_NAMES or "gemy" in low):
        return True
    if "turn" in words and "off" in words:
        return True
    return False


def _is_sad(low, words):
    if wants_turn_off(low, words, ""):
        return False
    if _is_mean(low, words):
        return False
    if words & SAD:
        return True
    if any(p in low for p in _SAD_PHRASES):
        return True
    for stem in ("lonely", "heartbroken", "goodbye forever", "nobody wants",
                 "no one wants", "feel sad", "so sad"):
        if stem in low:
            return True
    return False


def _is_mean(low, words):
    if wants_turn_off(low, words, ""):
        return False
    if any(p in low for p in ("shut down", "turn off", "power off")):
        return False
    if any(p in low for p in _SAD_NOT_MEAN_PHRASES):
        return False
    if words & MEAN:
        return True
    # Whole-word "mean" (not substring "meaning" / "meant").
    if "mean" in words:
        return True
    if any(phrase in low for phrase in _MEAN_PHRASES):
        return True
    # Strong insult stems often survive garbled STT.
    for stem in ("stupid", "idiot", "moron", "hate", "suck", "ugly", "shutup",
                 "shut up", "terrible", "awful", "worthless", "pathetic", "jerk"):
        if stem in low:
            return True
    return False


def _is_knock_knock(low, words):
    n = _norm_heard(low)
    if "knock knock" in n or "knockknock" in n.replace(" ", ""):
        return True
    if "noc noc" in n or "nock nock" in n:
        return True
    knocks = sum(1 for w in words if w == "knock" or w.startswith("knock"))
    return knocks >= 2


def _is_joke_setup(low):
    n = _norm_heard(low)
    return any(p in n for p in _JOKE_SETUP_PHRASES)


def _has_strong_joke_payoff(low):
    n = _norm_heard(low)
    if any(p in n for p in _JOKE_PAYOFF_PHRASES):
        return True
    if any(frag in n for frag in _JOKE_PUNCHLINE_FRAGMENTS):
        return True
    return False


def _is_joke_punchline(low, words):
    n = _norm_heard(low)
    if _has_strong_joke_payoff(low):
        return True
    if " who" in n or n.endswith(" who"):
        return True
    if any(len(w) > 4 and w.endswith("who") for w in words):
        return True
    # "banana who" / "orange who" — not the setup line "who's there"
    if "who" in words and "there" not in words and not words <= {"who", "whos"}:
        return True
    return False


def _is_complete_joke_utterance(low, words):
    """One heard phrase with setup + payoff (e.g. chicken cross the road joke)."""
    if _is_joke_setup(low) and _has_strong_joke_payoff(low):
        return True
    if "?" in low:
        setup, _, answer = low.partition("?")
        setup = setup.strip()
        answer = answer.strip()
        if answer and _is_joke_setup(setup) and (
            _has_strong_joke_payoff(answer) or len(answer.split()) >= 4
        ):
            return True
    return False


class KnockKnockTracker:
    """Track knock-knock and riddle jokes across one or more listen_once() turns."""

    def __init__(self, timeout_s=60.0):
        self.timeout_s = timeout_s
        self.active = False
        self.lines = 0
        self._started = 0.0
        self._riddle = False  # why did / what do you call — wait for payoff line

    def _expired(self):
        return self.active and (time.time() - self._started) > self.timeout_s

    def reset(self):
        self.active = False
        self.lines = 0
        self._started = 0.0
        self._riddle = False

    def start(self, riddle=False):
        self.active = True
        self.lines = 1
        self._riddle = riddle
        self._started = time.time()

    def on_line(self, low, words):
        """Return 'funny' at the punchline, or None to keep listening."""
        if self._expired():
            self.reset()
        if _is_complete_joke_utterance(low, words):
            self.reset()
            return "funny"
        if _is_knock_knock(low, words):
            if _is_joke_punchline(low, words):
                self.reset()
                return "funny"
            self.start(riddle=False)
            return None
        if _is_joke_setup(low):
            if _is_complete_joke_utterance(low, words):
                self.reset()
                return "funny"
            self.start(riddle=True)
            return None
        if not self.active:
            return None
        self.lines += 1
        self._started = time.time()
        if _is_joke_punchline(low, words) or _has_strong_joke_payoff(low):
            self.reset()
            return "funny"
        # Payoff after a riddle setup ("Why did the chicken...?" then "To get to the other side.")
        if self._riddle and self.lines >= 2 and len(words) >= 3:
            self.reset()
            return "funny"
        # Long payoff after knock-knock lines
        if not self._riddle and self.lines >= 3 and ("who" in words or len(words) >= 4):
            self.reset()
            return "funny"
        if not self._riddle and self.lines >= 5:
            self.reset()
            return "funny"
        return None


def _conversation_kind(low):
    """Small-talk without Gemma (avoids NPU fight with Moonshine)."""
    if any(p in low for p in _NICE_PHRASES):
        return "nice"
    if any(p in low for p in _CONVERSATION_GREET):
        return "greet"
    return None


def classify_keywords(low, words, greet_set, joke_tracker=None):
    """Fast keyword / knock-knock fallback when Gemma mood is off or unsure."""
    if _is_yes(low, words):
        return "yes"
    if _is_no(low, words):
        return "no"
    if joke_tracker is not None:
        joke_kind = joke_tracker.on_line(low, words)
        if joke_kind:
            return joke_kind
    if words & GEMY_NAMES or "gemy" in low:
        return "gemy"
    if _is_mean(low, words):
        if joke_tracker is not None:
            joke_tracker.reset()
        return "mean"
    if _is_sad(low, words):
        if joke_tracker is not None:
            joke_tracker.reset()
        return "sad"
    if (words & FUNNY) or "ha ha" in low \
            or any(w.startswith(("haha", "hehe", "lol")) for w in words):
        return "funny"
    if words & NICE or any(p in low for p in _NICE_PHRASES):
        return "nice"
    if words & greet_set:
        return "greet"
    return None


def classify_utterance(text, low, words, greet_set, joke_tracker=None, gemma_mood=None):
    """Turn-off → math → QA facts → yes/no → jokes → name → keywords → Gemma assist."""
    if wants_turn_off(low, words, text):
        if joke_tracker is not None:
            joke_tracker.reset()
        gemy_math.clear_math_context()
        return "off"
    if _is_greeting_with_name(low, words):
        if joke_tracker is not None:
            joke_tracker.reset()
        return "gemy"
    # Math before generic yes/no so "correct, is five plus five ten" stays a quiz.
    norm = _norm_heard(low)
    quiz = gemy_math.try_math_yes_no(low, words, n=norm)
    if quiz:
        if joke_tracker is not None:
            joke_tracker.reset()
        return quiz
    qa = gemy_qa.try_answer_yes_no(low, words)
    if qa:
        if joke_tracker is not None:
            joke_tracker.reset()
        return qa
    empathy = gemy_empathy.try_empathy_mood(low, words)
    if empathy:
        if joke_tracker is not None:
            joke_tracker.reset()
        return empathy
    if _is_yes(low, words):
        if joke_tracker is not None:
            joke_tracker.reset()
        return "yes"
    if _is_no(low, words):
        if joke_tracker is not None:
            joke_tracker.reset()
        return "no"
    if joke_tracker is not None:
        joke_kind = joke_tracker.on_line(low, words)
        if joke_kind:
            return joke_kind
    # Name before Gemma so "hi Gemy" gets short name ack, not a long greet + stuck buzzer risk.
    if words & GEMY_NAMES or "gemy" in low or "gemi" in low:
        if joke_tracker is not None:
            joke_tracker.reset()
        return "gemy"
    # Keywords first — drives hat beeps (funny / nice / mean / greet) without waiting on Gemma.
    kw = classify_keywords(low, words, greet_set, joke_tracker=None)
    if kw:
        return kw
    conv = _conversation_kind(low)
    if conv:
        if joke_tracker is not None:
            joke_tracker.reset()
        return conv
    return gemy_fallback.closest_beep_kind(low, words)


def resolve_reaction_kind(kind):
    """Map any label to a known beep reaction; unknown -> neutral (never crash react())."""
    return gemy_reactions.resolve_beep_kind(kind)


def _gemma_assist_timeout_s(gemma_mood=None) -> float:
    if _stability is not None:
        fn = getattr(_stability, "gemma_assist_timeout_s", None)
        if callable(fn):
            return fn(gemma_mood)
        return _stability.GEMMA_ASSIST_MAX_BLOCK_S
    return 90.0 if gemma_mood is not None and not getattr(
        gemma_mood, "_model_loaded", False
    ) else 15.0


def _gemma_allowed(text, low, words, joke_tracker) -> tuple[bool, str]:
    if _stability is not None:
        return _stability.gemma_assist_allowed(text, low, words, joke_tracker)
    stripped = low.strip()
    if len(stripped) < 6 and len(words) <= 1:
        return False, "fragment"
    if len(stripped) < 4:
        return False, "too short"
    return True, ""


def _maybe_gemma_assist(text, low, words, gemma_mood, joke_tracker, use_gemma_assist):
    """Gemma assist when keywords/math/QA missed."""
    if not use_gemma_assist or gemma_mood is None:
        return None
    math_quiz = gemy_math.looks_like_math_quiz(low)
    skip, skip_why = gemy_qa.should_skip_gemma_assist(low)
    if not skip and gemy_empathy.looks_like_personal_share(low):
        skip, skip_why = True, "personal_share"
    if skip:
        if skip_why == "local_qa":
            ans = gemy_qa.try_local_yes_no(low)
            if ans:
                print(f"[ears] local Q&A -> {ans} (skip Gemma).", flush=True)
                _diag("classify", f"local_qa {ans}")
                return ans
        print(
            f"[ears] {skip_why} question -> neutral, skip Gemma.",
            flush=True,
        )
        _diag("classify", f"skip gemma {skip_why}")
        return None
    if not math_quiz and gemy_reactions.looks_like_open_ended_question(low):
        print("[ears] open question (no yes/no beep) -> neutral, skip Gemma.", flush=True)
        _diag("classify", "open question skip gemma")
        return None
    allowed, skip_why = _gemma_allowed(text, low, words, joke_tracker)
    if not allowed:
        _diag("classify", f"gemma skip: {skip_why}")
        if gemy_qa.looks_like_question(low):
            print(f"[ears] question but skip Gemma ({skip_why}) -> neutral.", flush=True)
        else:
            print(f"[ears] skip Gemma ({skip_why}) -> neutral.", flush=True)
        return None
    if math_quiz:
        _diag("classify", "math quiz gemma assist (yes/no only)")
    elif gemy_qa.looks_like_question(low):
        _diag("classify", "gemma question assist")
    kind = try_gemma_mood_assist(text, gemma_mood, joke_tracker, low, words)
    if math_quiz and kind not in (None, "yes", "no", "off"):
        print(f"[ears] math quiz: Gemma said {kind!r} -> neutral.", flush=True)
        return None
    return kind


def try_gemma_mood_assist(text, gemma_mood, joke_tracker=None, low="", words=None):
    """Keywords missed — Gemma assist; never leave NPU busy after this returns."""
    if gemma_mood is None:
        return None
    words = words or set()
    allowed, why = _gemma_allowed(text, low, words, joke_tracker)
    if not allowed:
        _diag("gemma_skip", why)
        return None
    cooldown = getattr(gemma_mood, "_assist_cooldown_until", 0.0)
    if cooldown > time.time():
        _diag("gemma_skip", f"cooldown {cooldown - time.time():.0f}s left")
        return None
    if getattr(gemma_mood, "_classify_busy", False):
        print("[gemma] still checking last phrase; skipping assist.", flush=True)
        _diag("gemma_skip", "classify_busy")
        return None
    if not getattr(gemma_mood, "ready", False):
        state = getattr(gemma_mood, "_state", None)
        if state == "idle" and hasattr(gemma_mood, "start"):
            gemma_mood.start()
            ready_evt = getattr(gemma_mood, "_ready", None)
            if ready_evt is not None and not ready_evt.wait(timeout=30.0):
                return None
        if not getattr(gemma_mood, "ready", False):
            return None
    # Async Gemma: never block ears on first NPU load (preload runs in background).
    if not getattr(gemma_mood, "_model_loaded", False):
        print(
            "[gemma] still loading on NPU in background -> neutral (no freeze). "
            "Keywords/Q&A still work; try again in ~1 min.",
            flush=True,
        )
        _diag("gemma_skip", "model_not_loaded_yet")
        return None
    _diag_phase("gemma_assist", text[:60])
    _trace(
        "gemma_assist_start",
        text[:60]
        + (
            f" | {gemy_trace.npu_snapshot(gemma_mood)}"
            if gemy_trace is not None
            else ""
        ),
    )
    label = None
    try:
        timeout_s = _gemma_assist_timeout_s(gemma_mood)
        if not getattr(gemma_mood, "_model_loaded", False):
            print(
                "[gemma] first mood check (model loads on NPU, can take 1-3 min; "
                f"max {timeout_s:.0f}s then neutral)...",
                flush=True,
            )
        else:
            print(f"[gemma] checking mood (max {timeout_s:.0f}s, then neutral)...",
                  flush=True)
        label = gemma_mood.classify(text, infer_timeout_s=timeout_s)
    except Exception as e:
        print(f"[gemma] assist failed ({e}); neutral.", flush=True)
        _diag("gemma_assist_error", str(e))
        return None
    finally:
        if _stability is not None:
            _stability.finish_gemma_assist(gemma_mood)
        elif hasattr(gemma_mood, "release_npu"):
            gemma_mood.release_npu()
    _diag("gemma_assist", f"label={label!r}")
    label = gemy_reactions.gemma_label_to_beep_kind(label, low)
    if not label:
        return None
    if label == "off":
        return "off"
    label = resolve_reaction_kind(label)
    if label == "neutral":
        return None
    if joke_tracker is not None:
        joke_tracker.reset()
    return label


# ---- shared reaction dispatcher --------------------------------------------
class Greeter:
    def __init__(self, cooldown=3.0, idle_timeout=45.0, startup_grace_s=120.0):
        self.cooldown = cooldown
        self.idle_timeout = idle_timeout
        self.startup_grace_s = startup_grace_s
        self._lock = threading.Lock()
        self._last = 0.0
        now = time.time()
        self.last_activity = now
        self._started_at = now
        self._idle = False
        self._reacting = False
        self._vision_holdoff = 0.0

    def touch(self):
        """Mark activity so idle watchdog does not kill LEDs during startup/load."""
        with self._lock:
            self.last_activity = time.time()
            self._idle = False

    def abort_reaction(self) -> None:
        """Stuck-guard recovery: clear react lock so heartbeat/vision can resume."""
        with self._lock:
            self._reacting = False
            self.last_activity = time.time()

    def vision_allowed(self):
        with self._lock:
            return (not self._reacting) and (time.time() >= self._vision_holdoff)

    def react(self, kind, why=""):
        now = time.time()
        with self._lock:
            if self._reacting:
                _diag("react_skip", "already reacting")
                return
            if now - self._last < self.cooldown:
                _diag("react_skip", f"cooldown {self.cooldown - (now - self._last):.1f}s")
                return
            self._last = now
            self.last_activity = now
            self._idle = False
            self._reacting = True
        _diag_phase(f"react_{kind}", why[:80])
        _trace(f"react_{kind}_start", why[:80])
        print(f"[{time.strftime('%H:%M:%S')}] {_LABELS.get(kind, kind)}  ({kind} <- {why})")
        t0 = time.time()
        try:
            react_fn = REACTIONS.get(kind)
            if react_fn is None:
                print(
                    f"[gemy] no REACTIONS handler for {kind!r} — using neutral "
                    "(fix greeter.REACTIONS)",
                    flush=True,
                )
                react_fn = _react_neutral
            react_fn()
        except Exception as e:
            _diag("react_error", f"{kind} {e}")
            print(f"[gemy] reaction hardware error ({e}); continuing.", flush=True)
        finally:
            hat.force_all_off()
            with self._lock:
                self._reacting = False
            _diag("react_done", f"{kind} {time.time() - t0:.2f}s")
            _trace(f"react_{kind}_done", f"{time.time() - t0:.2f}s")

    def greet(self, why):
        self.react("greet", why)
        if why in ("wave", "hand up"):
            with self._lock:
                self._vision_holdoff = time.time() + 5.0

    def idle_check(self, gemma_mood=None):
        """Safety net: after a quiet stretch, make sure nothing is left on."""
        now = time.time()
        if gemma_mood is not None and getattr(gemma_mood, "loading", False):
            return
        if (now - self._started_at) < self.startup_grace_s:
            return
        if not self._idle and (now - self.last_activity) > self.idle_timeout:
            self._idle = True
            hat.buzzer_off()
            hat.led_off_all()
            print(f"[{time.strftime('%H:%M:%S')}] (idle) all LEDs off, buzzer off.")


# ---- vision: wave + hand held up -------------------------------------------
def count_reversals(xs, min_step):
    direction = 0
    reversals = 0
    anchor = xs[0]
    for x in xs[1:]:
        if x - anchor > min_step:
            if direction == -1:
                reversals += 1
            direction = 1
            anchor = x
        elif anchor - x > min_step:
            if direction == 1:
                reversals += 1
            direction = -1
            anchor = x
    return reversals


SENSITIVITY = {
    #            min_motion  reversals  min_step  window
    "low":      (0.010,      4,         0.10,     2.0),
    "medium":   (0.005,      3,         0.08,     2.2),
    "high":     (0.003,      3,         0.06,     2.5),
}


def open_camera(args):
    """Open + prime the camera and apply exposure/gain. Returns cap or None."""
    import cv2
    cap = cv2.VideoCapture(args.device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: could not open camera /dev/video{args.device} (vision off)")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    for _ in range(15):
        cap.read()
        time.sleep(0.02)
    hat._set_cam_ctrl("auto_exposure", 1)
    hat._set_cam_ctrl("gain_automatic", 0)
    hat._set_cam_ctrl("white_balance_automatic", 1)
    hat._set_cam_ctrl("exposure", int(args.exposure))
    hat._set_cam_ctrl("analogue_gain", int(args.gain))
    return cap


def vision_loop(greeter, args, stop_event, cap, gemma_mood=None):
    import cv2
    import numpy as np

    min_motion, need_reversals, min_step, window = SENSITIVITY[args.sensitivity]

    print(f"[vision] on (sensitivity={args.sensitivity}). Wave or hold a hand up.")

    prev = None
    bg = None
    positions = collections.deque()
    hand_since = None
    frames = 0
    t_start = time.time()
    last_status = 0.0

    # Hand-up tuning: lots of "foreground" in the upper region, held still.
    HAND_FG = 0.06           # >=6% of the upper region differs from background
    HAND_STILL = 0.012       # frame-to-frame motion below this = "held, not waving"
    HAND_HOLD_S = 0.7        # must persist this long

    # Cap the vision rate. Sleeping each iteration hands the 2 CPU cores back to
    # the speech thread (Moonshine/VAD) so the mic isn't starved; ~12 fps is
    # plenty to see a wave or a held-up hand.
    target_dt = (1.0 / args.fps) if getattr(args, "fps", 0) else 0.0
    next_t = time.time()

    fails = 0
    frame_n = 0
    try:
        while not stop_event.is_set():
            if gemma_mood is not None and (
                getattr(gemma_mood, "loading", False)
                or getattr(gemma_mood, "_classify_busy", False)
                or (
                    _stability is not None
                    and _stability.npu_held_by_gemma(gemma_mood)
                )
            ):
                time.sleep(0.25)
                continue
            if target_dt:
                sleep_for = next_t - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                next_t = time.time() + target_dt
            if args.duration and (time.time() - t_start) >= args.duration:
                stop_event.set()
                break
            ok, frame = cap.read()
            frame_n += 1
            if frame_n % 2 != 0:
                continue
            if not ok or frame is None:
                fails += 1
                if fails > 150:
                    print("\n[vision] camera stopped delivering frames; vision off.")
                    break
                time.sleep(0.01)
                continue
            fails = 0
            frames += 1
            now = time.time()

            # Downscale for cheap processing (ratios stay resolution-independent).
            if frame.shape[1] > 360:
                frame = cv2.resize(frame, (320, 240))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (15, 15), 0)
            if prev is None:
                prev = gray
                bg = gray.astype("float32")
                continue

            # consecutive-frame motion (for waving + "is it moving")
            delta = cv2.absdiff(prev, gray)
            prev = gray
            mthresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
            mthresh = cv2.dilate(mthresh, None, iterations=2)
            mxs = np.nonzero(mthresh)[1]
            motion_ratio = mxs.size / float(mthresh.size)

            # ---- wave: horizontal oscillation -------------------------------
            if motion_ratio > min_motion:
                cx = float(mxs.mean()) / mthresh.shape[1]
                positions.append((now, cx))
            while positions and now - positions[0][0] > window:
                positions.popleft()
            if greeter.vision_allowed() and len(positions) >= 5:
                seq = [c for _, c in positions]
                if (max(seq) - min(seq) >= 0.15
                        and count_reversals(seq, min_step) >= need_reversals):
                    greeter.greet("wave")
                    positions.clear()

            # ---- hand held up: sustained still foreground in upper region ---
            cv2.accumulateWeighted(gray, bg, 0.05)
            fg = cv2.absdiff(gray, cv2.convertScaleAbs(bg))
            fgmask = cv2.threshold(fg, 30, 255, cv2.THRESH_BINARY)[1]
            h = fgmask.shape[0]
            upper = fgmask[0:int(h * 0.55), :]
            fg_upper = np.count_nonzero(upper) / float(upper.size)
            if fg_upper > HAND_FG and motion_ratio < HAND_STILL:
                if hand_since is None:
                    hand_since = now
                elif greeter.vision_allowed() and now - hand_since >= HAND_HOLD_S:
                    greeter.greet("hand up")
                    hand_since = None
            else:
                hand_since = None

            if not args.quiet and (now - last_status) > 1.0:
                fps = frames / (now - t_start)
                print(f"\r[vision] {fps:4.1f} fps  motion {motion_ratio*100:4.1f}%  "
                      f"upperFG {fg_upper*100:4.1f}%   ", end="", flush=True)
                last_status = now

    finally:
        stop_event.set()   # ensure other threads wind down if vision exits


# ---- ears: listen for speech (load model BEFORE camera when possible) ------
def _run_gemma_heartbeat_while(loading_flag, greeter, stop_event):
    """Blink red LED while loading_flag[0] is True."""
    _diag("heartbeat_thread", "gemma-load start")
    while loading_flag[0] and not stop_event.is_set():
        if greeter is not None:
            greeter.touch()
        try:
            hat.hold_led("red", 0.12)
            if gemy_diag is not None:
                gemy_diag.mark_heartbeat_pulse("gemma-init")
        except Exception as e:
            _diag("heartbeat_error", str(e))
        if stop_event.wait(1.4):
            break
    _diag("heartbeat_thread", "gemma-load end (flag cleared or stop)")


def init_gemma_mood(args, greeter, heartbeat_stop):
    """Optional Gemma mood labels (only when --gemma-mood-assist)."""
    if getattr(args, "no_gemma_mood", False):
        print("[gemma] off - keyword moods only.", flush=True)
        return None
    if not getattr(args, "gemma_mood_assist", False):
        return None
    if getattr(args, "gemma_mood_serial", False):
        print("[gemma] --gemma-mood-serial is disabled (NPU freeze risk). Keywords only.", flush=True)
        return None
    try:
        from gemma_mood import (
            GemmaMoodSubprocess,
            create_gemma_mood_loader,
            load_gemma_before_speech,
        )
    except ImportError as e:
        print(f"[gemma] mood unavailable ({e}); keywords only.", flush=True)
        return None

    timeout = getattr(args, "gemma_mood_timeout", 180.0)
    greeter.touch()

    # Legacy: load after [ears] (can freeze — use only for experiments).
    if getattr(args, "gemma_defer", False):
        print("[gemma] deferred load after [ears] (--gemma-defer).", flush=True)
        return create_gemma_mood_loader(timeout)

    # Subprocess: lazy worker (READY fast; model loads on first classify only).
    if not getattr(args, "gemma_in_process", False):
        worker = GemmaMoodSubprocess(timeout_s=timeout)
        print("[gemma] assist on - keywords first; Gemma if unclear (invalid -> neutral).",
              flush=True)
        print(
            "[stability] Gemma worker warm-starts; model unloads after each assist "
            "(worker kept for speed). "
            f"Max {_gemma_assist_timeout_s(worker):.0f}s first load / "
            f"{_gemma_assist_timeout_s():.0f}s per check; NPU free while listening.",
            flush=True,
        )
        return worker

    # In-process: load on main thread (not recommended on 2GB board).
    loading_box = [True]
    threading.Thread(
        target=_run_gemma_heartbeat_while,
        args=(loading_box, greeter, heartbeat_stop),
        name="gemma-heartbeat",
        daemon=True,
    ).start()
    try:
        return load_gemma_before_speech(on_progress=lambda: greeter.touch())
    finally:
        loading_box[0] = False


def _gemma_load_heartbeat(stop_event, gemma_mood, greeter=None):
    """Blink red LED while Gemma loads so the board looks alive (each pulse < 2s)."""
    _diag("heartbeat_thread", "gemma-defer start")
    while not stop_event.is_set():
        if gemma_mood is None or not getattr(gemma_mood, "loading", False):
            _diag("heartbeat_thread", "gemma-defer end (not loading)")
            break
        if greeter is not None:
            greeter.touch()
        try:
            hat.hold_led("red", 0.12)
            if gemy_diag is not None:
                gemy_diag.mark_heartbeat_pulse("gemma-defer")
        except Exception as e:
            _diag("heartbeat_error", str(e))
        if stop_event.wait(1.4):
            _diag("heartbeat_thread", "gemma-defer stop_event")
            break


def _start_deferred_gemma(gemma_mood, args, stop_event, heartbeat_stop, greeter=None):
    """Start background Gemma load once ears are up; optional delay for stability."""
    if gemma_mood is None:
        return
    if getattr(gemma_mood, "ready", False) or getattr(gemma_mood, "loading", False):
        return
    if getattr(gemma_mood, "_state", None) != "idle":
        return
    delay = max(0.0, float(getattr(args, "gemma_delay", 8.0)))
    if delay > 0:
        print(f"[gemma] starting mood load in {delay:.0f}s (vision pauses meanwhile)...",
              flush=True)
        if stop_event.wait(delay):
            return
    print("[gemma] loading Gemma 3 on NPU now (red LED = heartbeat)...", flush=True)
    if greeter is not None:
        greeter.touch()
    timeout = getattr(args, "gemma_mood_timeout", 180.0)
    gemma_mood.start_background(timeout)
    threading.Thread(
        target=_gemma_load_heartbeat,
        args=(heartbeat_stop, gemma_mood, greeter),
        name="gemma-heartbeat",
        daemon=True,
    ).start()


def build_speech(args):
    """Load Moonshine + mic. Call in main thread before vision hogs CPU."""
    try:
        from utils.speech import (
            MoonshineTranscriber, SileroSpeechSegmenter,
            SoundDeviceAudioSource, SpeechRecognizer,
        )
    except Exception as e:
        print(f"[ears] speech unavailable ({e})")
        return None, None

    device = args.audio_device
    if device is not None:
        try:
            device = int(device)
        except ValueError:
            pass

    print("[ears] loading speech model (~10-20s)...", flush=True)
    try:
        transcriber = MoonshineTranscriber(None, suppress_native_logs=True)
        source = SoundDeviceAudioSource(device=device, suppress_native_logs=True)
        segmenter = SileroSpeechSegmenter()
        recognizer = SpeechRecognizer(transcriber=transcriber, source=source,
                                      segmenter=segmenter)
        print("[ears] model ready.", flush=True)
        return recognizer, source
    except Exception as e:
        print(f"[ears] could not start microphone ({e})")
        return None, None


def speech_loop(greeter, args, stop_event, recognizer, source, gemma_mood=None,
                heartbeat_stop=None):
    keywords = set(k.strip().lower() for k in args.keywords.split(","))
    joke_tracker = KnockKnockTracker()
    phrase_buffer = gemy_phrase_buffer.PhraseBuffer()
    # Default: local moods only (every phrase -> beep; no NPU). Gemma is opt-in.
    use_gemma_assist = bool(
        gemma_mood
        and getattr(args, "gemma_mood_assist", False)
        and not getattr(args, "no_gemma_mood", False)
    )
    if use_gemma_assist:
        mood_src = "keywords + yes/no + Gemma assist on neutral only (experimental)"
    else:
        mood_src = "keywords + yes/no + empathy + closest/neutral (no NPU)"
    print(f"[ears] listening (moods: {mood_src}).", flush=True)
    greeter.touch()
    if use_gemma_assist and hasattr(gemma_mood, "warm_worker"):
        def _warm():
            # Let the user say "hi Gemy" before background NPU preload (avoids NPU fight).
            _trace("gemma_warm_wait", "25s before worker+preload")
            if stop_event.wait(25.0):
                return
            _trace("gemma_warm_start", "warm_worker")
            gemma_mood.warm_worker()
            preload = getattr(gemma_mood, "start_background_preload", None)
            if callable(preload):
                print(
                    "[gemma] background preload started (ears stay responsive; "
                    "assist when load finishes).",
                    flush=True,
                )
                _trace("gemma_preload_start", "timeout=120s")
                preload(timeout_s=120.0)
        threading.Thread(target=_warm, name="gemma-warm", daemon=True).start()
    elif (
        heartbeat_stop is not None
        and hasattr(gemma_mood, "start_background")
        and getattr(gemma_mood, "_state", None) == "idle"
    ):
        _start_deferred_gemma(gemma_mood, args, stop_event, heartbeat_stop, greeter)
    print(f"[ears] Say hello, yes/no, jokes, nice/mean/sad things, or 'Gemy turn off'.",
          flush=True)
    print(f"[ears] Say 'Gemy turn off' (or 'stop') to end the demo.", flush=True)
    if use_gemma_assist:
        print(
            "[ears] Quiz tip: say the full question in one breath "
            "(e.g. 'is the sky green'). Short cuts like 'is the sky' -> neutral.",
            flush=True,
        )
    try:
        with recognizer:
            while not stop_event.is_set():
                if _stability is not None and _stability.npu_held_by_gemma(gemma_mood):
                    _trace(
                        "npu_busy_before_listen",
                        gemy_trace.npu_snapshot(gemma_mood)
                        if gemy_trace is not None else "",
                    )
                    _stability.ensure_npu_for_ears(gemma_mood)
                _diag_phase("listen_wait", "Moonshine listen_once")
                t0_listen = time.time()
                try:
                    if _stability is not None:
                        t = _stability.listen_once_timed(
                            recognizer, source, stop_event, gemma_mood
                        )
                    else:
                        t = recognizer.listen_once(stop_event=stop_event)
                except Exception as listen_err:
                    _diag("listen_error", str(listen_err))
                    err_s = str(listen_err)
                    print(f"[ears] listen error ({listen_err}); recovering.", flush=True)
                    if _stability is not None:
                        _stability.recover_audio_source(source)
                        _stability.ensure_npu_for_ears(gemma_mood)
                    if "failed to acquire hardware" in err_s:
                        print(
                            "[ears] NPU busy — waiting for Gemma preload to yield, then retry.",
                            flush=True,
                        )
                        time.sleep(1.0)
                    continue
                listen_s = time.time() - t0_listen
                if t is None:
                    if stop_event.is_set():
                        _diag("listen", "None (stop)")
                        break
                    _trace("listen_timeout", f"after {listen_s:.1f}s")
                    _diag("listen", f"timeout/recovery after {listen_s:.1f}s")
                    continue
                text = t.text.strip()
                if not text:
                    _trace("listen_empty", f"after {listen_s:.1f}s")
                    _diag("listen", f"empty after {listen_s:.1f}s")
                    continue
                _trace("listen_ok", f"{listen_s:.1f}s text={text[:60]!r}")
                _diag("listen_done", f"{listen_s:.1f}s text={text[:60]!r}")
                if gemy_trace is not None:
                    gemy_trace.mark_ears_heard(text)
                elif gemy_diag is not None:
                    gemy_diag.mark_ears_heard(text)
                _diag_phase("classify", text[:60])
                merged = False
                low, words = _words_from_text(text)
                t_buf, low, words, merged = phrase_buffer.absorb(text, low, words)
                if merged:
                    text = t_buf
                    print(f"[ears] merged phrase: {text!r}", flush=True)
                    _diag("listen", f"merged {text[:60]!r}")
                kind = gemy_classify.classify_heard(
                    text,
                    greet_keywords=keywords,
                    joke_tracker=joke_tracker,
                    use_gemma_assist=use_gemma_assist,
                    gemma_mood=gemma_mood if use_gemma_assist else None,
                )
                _diag("classify", f"kind={kind!r}")
                _trace("classify_done", f"kind={kind!r}")
                if kind == "off":
                    print(f"\n[ears] heard: {text!r} -> off (shutting down)", flush=True)
                    print("[gemy] Goodbye!", flush=True)
                    hat.gemy_goodbye()
                    stop_event.set()
                    break
                if joke_tracker.active and kind == "neutral":
                    print("[ears] (knock-knock in progress — keep going to the punchline)", flush=True)
                print(f"\n[ears] heard: {text!r} -> {kind}", flush=True)
                hat.force_all_off()
                try:
                    greeter.react(kind, f'heard "{text}"')
                except Exception as react_err:
                    print(f"[gemy] reaction error ({react_err}); continuing.",
                          flush=True)
                    hat.force_all_off()
                if (
                    use_gemma_assist
                    and kind == "neutral"
                    and hasattr(gemma_mood, "start_prewarm_background")
                    and _stability is not None
                    and not _stability.npu_held_by_gemma(gemma_mood)
                ):
                    gemma_mood.start_prewarm_background(timeout_s=50.0)
    except Exception as e:
        import traceback
        err = str(e)
        _diag_phase("ears_crashed", err[:120])
        print(f"[ears] stopped: {e}", flush=True)
        if "failed to acquire hardware" in err:
            print("[ears] NPU busy (Moonshine + Gemma cannot both use it).", flush=True)
            print("[ears] Restart without --moonshine-npu, or use --no-gemma-mood.", flush=True)
        traceback.print_exc()
    finally:
        _diag("ears_loop", "exit")
        try:
            source.stop()
        except Exception as src_err:
            _diag("ears_cleanup", f"source.stop: {src_err}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Gemy — greeting robot (wave / hand-up / voice)")
    p.add_argument("--device", type=int, default=0, help="camera /dev/videoN")
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--exposure", type=int, default=740)
    p.add_argument("--gain", type=int, default=1023)
    p.add_argument("--sensitivity", choices=list(SENSITIVITY), default="medium")
    p.add_argument("--fps", type=float, default=5.0,
                   help="cap vision frame rate so the mic gets CPU (0=uncapped)")
    p.add_argument("--cooldown", type=float, default=1.0,
                   help="min seconds between reactions (lower = more responsive)")
    p.add_argument("--keywords", default="hello,hi,hey,hiya")
    p.add_argument("--audio-device", default=None, help="mic index/name (default: system default)")
    p.add_argument("--no-speech", action="store_true", help="disable the microphone trigger")
    p.add_argument("--no-gemma-mood", action="store_true",
                   help="disable Gemma mood assist (keywords only)")
    p.add_argument("--gemma-mood", action="store_true",
                   help=argparse.SUPPRESS)  # legacy; use --gemma-mood-assist
    p.add_argument("--gemma-mood-assist", action="store_true",
                   help="experimental: Gemma on neutral only (NPU risk; default off)")
    p.add_argument("--gemma-mood-serial", action="store_true",
                   help=argparse.SUPPRESS)
    p.add_argument("--gemma-in-process", action="store_true",
                   help="load Gemma inside greeter before speech (not recommended on 2GB)")
    p.add_argument("--gemma-defer", action="store_true",
                   help="old: load Gemma after [ears] (may freeze; not recommended)")
    p.add_argument("--gemma-mood-timeout", type=float, default=180.0,
                   help="seconds to wait for Gemma load (then keywords only)")
    p.add_argument("--gemma-delay", type=float, default=8.0,
                   help="only with --gemma-defer: seconds after [ears] before load")
    p.add_argument("--no-vision", action="store_true", help="disable the camera triggers")
    p.add_argument("--duration", type=float, default=0.0, help="auto-stop after N s (0=forever)")
    p.add_argument("--idle-timeout", type=float, default=45.0,
                   help="after N s of no reaction, force LEDs + buzzer off")
    p.add_argument("--startup-grace", type=float, default=60.0,
                   help="do not idle-force-off for this long after start")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--no-intro", action="store_true",
                   help="skip the hello-this-is-Gemy startup beep/light sequence")
    p.add_argument("--pc-start", action="store_true",
                   help="started from PC greet-demo: short intro, no boot autostart fight")
    p.add_argument("--diag", action="store_true",
                   help="verbose [diag] phase logging (on by default with --pc-start)")
    p.add_argument("--no-diag", action="store_true",
                   help="disable [diag] logging")
    args = p.parse_args(argv)

    if gemy_diag is not None and not args.no_diag and (args.diag or args.pc_start):
        gemy_diag.set_enabled(True)

    _stop_stale_demos()
    _diag("main", f"pid={os.getpid()} speech={not args.no_speech} vision={not args.no_vision}")

    greeter = Greeter(
        cooldown=args.cooldown,
        idle_timeout=args.idle_timeout,
        startup_grace_s=args.startup_grace,
    )
    stop_event = threading.Event()

    print("Gemy starting. Triggers: "
          + ("wave + hand-up" if not args.no_vision else "")
          + (" + " if (not args.no_vision and not args.no_speech) else "")
          + ('say "Gemy" / hello / hi / ...' if not args.no_speech else "")
          + ". Ctrl+C to stop.")

    # Moonshine STT first; optional Gemma mood assist only when enabled (shares NPU if used).
    recognizer = source = None
    gemma_mood = None
    gemma_heartbeat_stop = threading.Event()

    if not args.no_speech:
        recognizer, source = build_speech(args)
        if recognizer is None:
            args.no_speech = True

    if not args.no_speech and getattr(args, "gemma_mood_assist", False):
        gemma_mood = init_gemma_mood(args, greeter, gemma_heartbeat_stop)
    elif not args.no_speech:
        print(
            "[gemma] off — every phrase maps locally (neutral or closest beep). "
            "Use --gemma-mood-assist to experiment with NPU mood.",
            flush=True,
        )

    if not args.no_intro and not args.no_speech:
        print("[gemy] Hello! This is Gemy.", flush=True)
        hat.force_all_off()
        if getattr(args, "pc_start", False):
            hat.gemy_intro_short()
        else:
            hat.gemy_intro()
        hat.force_all_off()
        greeter.touch()

    cap = None
    if not args.no_vision:
        cap = open_camera(args)
        if cap is None:
            args.no_vision = True
            print("[vision] OFF (camera busy or missing). Voice still works.")

    def idle_loop():
        while not stop_event.is_set():
            greeter.idle_check(gemma_mood)
            time.sleep(0.4)

    threads = []
    if recognizer is not None:
        threads.append(threading.Thread(target=speech_loop,
                                        args=(greeter, args, stop_event,
                                              recognizer, source, gemma_mood,
                                              gemma_heartbeat_stop),
                                        name="ears", daemon=True))
    threads.append(threading.Thread(target=idle_loop, name="idle", daemon=True))
    for t in threads:
        t.start()
    if gemy_trace is not None:
        gemy_trace.start_watchdog(stop_event, gemma_mood, greeter, interval_s=30.0)
        _trace("trace_on", "grep [trace] in /home/root/gemy.log (GEMY_TRACE=0 to disable)")
    if gemy_diag is not None and gemy_diag.enabled():
        gemy_diag.start_watchdog(stop_event, gemma_mood, greeter, interval_s=20.0)
    if _stability is not None:
        _stability.start_session_heartbeat(stop_event, greeter)
        if not args.no_speech:
            _stability.start_stuck_guard(stop_event, gemma_mood, greeter, source)

    try:
        if args.no_vision:
            t0 = time.time()
            while not stop_event.is_set():
                time.sleep(0.2)
                if args.duration and (time.time() - t0) >= args.duration:
                    break
        else:
            vision_loop(greeter, args, stop_event, cap, gemma_mood)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        _diag("main", "shutdown")
        gemma_heartbeat_stop.set()
        stop_event.set()
        for t in threads:
            t.join(timeout=2.0)
        if cap is not None:
            cap.release()
        if gemma_mood is not None and hasattr(gemma_mood, "stop"):
            try:
                gemma_mood.stop()
            except Exception:
                pass
        hat.force_all_off()
    return 0


if __name__ == "__main__":
    sys.exit(main())
