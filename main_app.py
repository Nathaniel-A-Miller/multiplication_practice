import streamlit as st
import random
import time
import json
import os
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
TOTAL_QUESTIONS = 10
LEADERBOARD_FILE = "leaderboard.json"
MAX_LEADERS = 10

st.set_page_config(page_title="Multiplication Blitz", page_icon="⏱️", layout="centered")

# ── Leaderboard helpers ──────────────────────────────────────────────────────
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE) as f:
            return json.load(f)
    return {"type": [], "mc": []}

def save_leaderboard(lb):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(lb, f, indent=2)

def add_to_leaderboard(name, elapsed, mode):
    lb = load_leaderboard()
    key = "type" if mode == "Type" else "mc"
    lb[key].append({"name": name, "time": elapsed, "date": datetime.now().strftime("%b %d %Y")})
    lb[key].sort(key=lambda x: x["time"])
    lb[key] = lb[key][:MAX_LEADERS]
    save_leaderboard(lb)
    return lb

def get_rank(elapsed, mode):
    lb = load_leaderboard()
    key = "type" if mode == "Type" else "mc"
    times = [e["time"] for e in lb[key]]
    times_sorted = sorted(times)
    try:
        return times_sorted.index(elapsed) + 1
    except ValueError:
        return None

# ── Question helpers ─────────────────────────────────────────────────────────
def new_question():
    a = random.randint(1, 12)
    b = random.randint(1, 12)
    return a, b

def make_choices(a, b):
    correct = a * b
    distractors = set()
    while len(distractors) < 3:
        delta = random.choice([-3, -2, -1, 1, 2, 3])
        wrong = correct + delta
        if wrong > 0 and wrong != correct:
            distractors.add(wrong)
    options = list(distractors) + [correct]
    random.shuffle(options)
    return options, correct

# ── Session state init ───────────────────────────────────────────────────────
def init_state():
    defaults = {
        "screen": "start",       # start | game | result
        "player_name": "",
        "mode": "Type",
        "questions": [],
        "q_index": 0,
        "start_time": None,
        "elapsed": None,
        "wrong_flash": False,
        "correct_flash": False,
        "mc_options": [],
        "new_entry_rank": None,
        "leaderboard": load_leaderboard(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.big-problem {
    font-size: 4rem;
    font-weight: 900;
    text-align: center;
    letter-spacing: -2px;
    padding: 1.5rem 0 0.5rem;
    color: #1a1a2e;
}
.timer-display {
    font-size: 1.6rem;
    font-weight: 700;
    text-align: center;
    color: #e94560;
    letter-spacing: 2px;
    margin-bottom: 0.5rem;
}
.progress-label {
    text-align: center;
    font-size: 0.9rem;
    color: #888;
    margin-bottom: 1.5rem;
}
.flash-wrong {
    background: #ffe0e0;
    border-radius: 12px;
    padding: 0.3rem 1rem;
    text-align: center;
    color: #c0392b;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.flash-correct {
    background: #e0ffe8;
    border-radius: 12px;
    padding: 0.3rem 1rem;
    text-align: center;
    color: #27ae60;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.result-time {
    font-size: 3.5rem;
    font-weight: 900;
    text-align: center;
    color: #e94560;
    margin: 0.5rem 0;
}
.result-rank {
    text-align: center;
    font-size: 1.3rem;
    font-weight: 600;
    color: #1a1a2e;
    margin-bottom: 1rem;
}
.lb-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1a2e;
    border-bottom: 2px solid #e94560;
    padding-bottom: 4px;
    margin-bottom: 8px;
}
.lb-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 4px;
    border-radius: 6px;
    font-size: 0.92rem;
}
.lb-row-highlight {
    background: #fff3cd;
    font-weight: 700;
}
.lb-rank { width: 30px; color: #888; }
.lb-name { flex: 1; }
.lb-time { color: #e94560; font-weight: 600; width: 70px; text-align: right; }
.lb-date { color: #aaa; font-size: 0.8rem; width: 90px; text-align: right; }
</style>
""", unsafe_allow_html=True)

# ── START SCREEN ─────────────────────────────────────────────────────────────
if st.session_state.screen == "start":
    st.title("⏱️ Multiplication Blitz")
    st.markdown("Answer **10 multiplication questions** as fast as you can. Wrong answers keep you on the same question until you get it right.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your name", max_chars=20, placeholder="Enter your name")
    with col2:
        mode = st.radio("Answer mode", ["Type", "Multiple Choice"], horizontal=True)

    st.markdown("")
    if st.button("🚀 Start Game", use_container_width=True, type="primary"):
        if not name.strip():
            st.warning("Please enter your name.")
        else:
            questions = [new_question() for _ in range(TOTAL_QUESTIONS)]
            st.session_state.update({
                "player_name": name.strip(),
                "mode": mode,
                "questions": questions,
                "q_index": 0,
                "start_time": time.time(),
                "elapsed": None,
                "wrong_flash": False,
                "correct_flash": False,
                "screen": "game",
            })
            if mode == "Multiple Choice":
                a, b = questions[0]
                opts, _ = make_choices(a, b)
                st.session_state.mc_options = opts
            st.rerun()

    # Show leaderboard on start screen
    st.divider()
    lb = load_leaderboard()
    c1, c2 = st.columns(2)
    for col, key, label in [(c1, "type", "Type Mode"), (c2, "mc", "Multiple Choice")]:
        with col:
            st.markdown(f'<div class="lb-title">🏆 {label}</div>', unsafe_allow_html=True)
            entries = lb.get(key, [])
            if not entries:
                st.caption("No scores yet.")
            for i, e in enumerate(entries):
                mins, secs = divmod(e["time"], 60)
                time_str = f"{int(mins)}:{secs:05.2f}" if mins else f"{secs:.2f}s"
                st.markdown(
                    f'<div class="lb-row">'
                    f'<span class="lb-rank">#{i+1}</span>'
                    f'<span class="lb-name">{e["name"]}</span>'
                    f'<span class="lb-time">{time_str}</span>'
                    f'<span class="lb-date">{e["date"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

# ── GAME SCREEN ──────────────────────────────────────────────────────────────
elif st.session_state.screen == "game":
    q_idx = st.session_state.q_index
    a, b = st.session_state.questions[q_idx]
    correct = a * b
    elapsed_now = time.time() - st.session_state.start_time

    mins, secs = divmod(elapsed_now, 60)
    time_str = f"{int(mins)}:{secs:05.2f}" if mins else f"{secs:.2f}s"

    st.markdown(f'<div class="timer-display">⏱️ {time_str}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-label">Question {q_idx + 1} of {TOTAL_QUESTIONS}</div>', unsafe_allow_html=True)
    st.progress((q_idx) / TOTAL_QUESTIONS)

    st.markdown(f'<div class="big-problem">{a} × {b} = ?</div>', unsafe_allow_html=True)

    if st.session_state.wrong_flash:
        st.markdown('<div class="flash-wrong">✗ Not quite — try again!</div>', unsafe_allow_html=True)
        st.session_state.wrong_flash = False

    # ── Type mode
    if st.session_state.mode == "Type":
        with st.form("answer_form", clear_on_submit=True):
            answer_input = st.number_input("Your answer", step=1, value=0, label_visibility="collapsed")
            submitted = st.form_submit_button("Submit", use_container_width=True, type="primary")

        if submitted:
            if int(answer_input) == correct:
                next_idx = q_idx + 1
                if next_idx >= TOTAL_QUESTIONS:
                    elapsed = time.time() - st.session_state.start_time
                    st.session_state.elapsed = elapsed
                    lb = add_to_leaderboard(st.session_state.player_name, elapsed, st.session_state.mode)
                    st.session_state.leaderboard = lb
                    st.session_state.new_entry_rank = get_rank(elapsed, st.session_state.mode)
                    st.session_state.screen = "result"
                else:
                    st.session_state.q_index = next_idx
                st.rerun()
            else:
                st.session_state.wrong_flash = True
                st.rerun()

    # ── Multiple choice mode
    else:
        options = st.session_state.mc_options
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if st.button(str(opt), key=f"mc_{opt}_{q_idx}", use_container_width=True):
                    if opt == correct:
                        next_idx = q_idx + 1
                        if next_idx >= TOTAL_QUESTIONS:
                            elapsed = time.time() - st.session_state.start_time
                            st.session_state.elapsed = elapsed
                            lb = add_to_leaderboard(st.session_state.player_name, elapsed, st.session_state.mode)
                            st.session_state.leaderboard = lb
                            st.session_state.new_entry_rank = get_rank(elapsed, st.session_state.mode)
                            st.session_state.screen = "result"
                        else:
                            st.session_state.q_index = next_idx
                            na, nb = st.session_state.questions[next_idx]
                            opts, _ = make_choices(na, nb)
                            st.session_state.mc_options = opts
                        st.rerun()
                    else:
                        st.session_state.wrong_flash = True
                        st.rerun()

    # Auto-refresh every second to keep timer ticking
    time.sleep(0.5)
    st.rerun()

# ── RESULT SCREEN ─────────────────────────────────────────────────────────────
elif st.session_state.screen == "result":
    elapsed = st.session_state.elapsed
    mins, secs = divmod(elapsed, 60)
    time_str = f"{int(mins)}:{secs:05.2f}" if mins else f"{secs:.2f}s"
    rank = st.session_state.new_entry_rank
    mode = st.session_state.mode

    st.title("🎉 Round Complete!")
    st.markdown(f'<div class="result-time">{time_str}</div>', unsafe_allow_html=True)

    if rank == 1:
        st.markdown('<div class="result-rank">🥇 New #1 all-time! Incredible!</div>', unsafe_allow_html=True)
    elif rank and rank <= 3:
        st.markdown(f'<div class="result-rank">🏅 #{rank} all-time — top of the podium!</div>', unsafe_allow_html=True)
    elif rank and rank <= MAX_LEADERS:
        st.markdown(f'<div class="result-rank">🏆 #{rank} on the leaderboard!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="result-rank">Keep practicing — the leaderboard awaits!</div>', unsafe_allow_html=True)

    st.divider()

    # Leaderboard
    lb = st.session_state.leaderboard
    key = "type" if mode == "Type" else "mc"
    st.markdown(f'<div class="lb-title">🏆 {mode} Mode — Top {MAX_LEADERS}</div>', unsafe_allow_html=True)
    for i, e in enumerate(lb.get(key, [])):
        mins2, secs2 = divmod(e["time"], 60)
        t = f"{int(mins2)}:{secs2:05.2f}" if mins2 else f"{secs2:.2f}s"
        is_new = (i + 1 == rank and e["name"] == st.session_state.player_name)
        row_class = "lb-row lb-row-highlight" if is_new else "lb-row"
        new_tag = " ← you" if is_new else ""
        st.markdown(
            f'<div class="{row_class}">'
            f'<span class="lb-rank">#{i+1}</span>'
            f'<span class="lb-name">{e["name"]}{new_tag}</span>'
            f'<span class="lb-time">{t}</span>'
            f'<span class="lb-date">{e["date"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Play Again (same settings)", use_container_width=True, type="primary"):
            questions = [new_question() for _ in range(TOTAL_QUESTIONS)]
            st.session_state.update({
                "questions": questions,
                "q_index": 0,
                "start_time": time.time(),
                "elapsed": None,
                "wrong_flash": False,
                "screen": "game",
            })
            if st.session_state.mode == "Multiple Choice":
                a, b = questions[0]
                opts, _ = make_choices(a, b)
                st.session_state.mc_options = opts
            st.rerun()
    with col2:
        if st.button("🏠 Change Settings", use_container_width=True):
            st.session_state.screen = "start"
            st.rerun()
