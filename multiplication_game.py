import streamlit as st
import random
import time
from datetime import datetime
from supabase import create_client, Client

# ── Config ───────────────────────────────────────────────────────────────────
TOTAL_QUESTIONS = 25
MAX_LEADERS = 10
MC_PENALTY_SECONDS = 5

st.set_page_config(page_title="Multiplication Blitz", page_icon="⏱️", layout="centered")

# ── Supabase client ───────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def load_leaderboard():
    sb = get_supabase()
    result = {"type": [], "mc": []}
    for mode_key in ["type", "mc"]:
        rows = (
            sb.table("leaderboard")
            .select("*")
            .eq("mode", mode_key)
            .order("time", desc=False)
            .limit(MAX_LEADERS)
            .execute()
        )
        result[mode_key] = rows.data
    return result

def add_to_leaderboard(name, elapsed, mode):
    sb = get_supabase()
    mode_key = "type" if mode == "Type" else "mc"
    sb.table("leaderboard").insert({
        "name": name,
        "time": round(elapsed, 3),
        "mode": mode_key,
        "date": datetime.now().strftime("%b %d %Y"),
    }).execute()
    return load_leaderboard()

def get_rank(elapsed, mode):
    lb = load_leaderboard()
    key = "type" if mode == "Type" else "mc"
    times = sorted([e["time"] for e in lb[key]])
    try:
        return times.index(round(elapsed, 3)) + 1
    except ValueError:
        return None

# ── Question helpers ──────────────────────────────────────────────────────────
def new_question():
    return random.randint(1, 12), random.randint(1, 12)

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

# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "screen": "start",
        "player_name": "",
        "mode": "Type",
        "questions": [],
        "q_index": 0,
        "start_time": None,
        "elapsed": None,
        "wrong_flash": False,
        "penalty_flash": False,   # NEW: triggers the +5s penalty banner
        "time_penalty": 0.0,      # NEW: accumulated penalty seconds
        "mc_options": [],
        "new_entry_rank": None,
        "leaderboard": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── CSS ───────────────────────────────────────────────────────────────────────
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
.flash-penalty {
    background: #ff4500;
    border-radius: 12px;
    padding: 0.5rem 1rem;
    text-align: center;
    color: #ffffff;
    font-size: 1.3rem;
    font-weight: 900;
    margin-bottom: 0.5rem;
    letter-spacing: 1px;
    animation: pulse 0.3s ease-in-out;
}
@keyframes pulse {
    0%   { transform: scale(1); }
    50%  { transform: scale(1.04); }
    100% { transform: scale(1); }
}
.result-time {
    font-size: 3.5rem;
    font-weight: 900;
    text-align: center;
    color: #e94560;
    margin: 0.5rem 0;
}
.result-penalty-note {
    text-align: center;
    font-size: 0.95rem;
    color: #888;
    margin-bottom: 0.5rem;
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

# ── Helpers ───────────────────────────────────────────────────────────────────
def format_time(seconds):
    mins, secs = divmod(seconds, 60)
    return f"{int(mins)}:{secs:05.2f}" if mins else f"{secs:.2f}s"

def render_leaderboard(lb, mode, highlight_rank=None, highlight_name=None):
    key = "type" if mode == "Type" else "mc"
    label = "Type Mode" if mode == "Type" else "Multiple Choice"
    st.markdown(f'<div class="lb-title">🏆 {label}</div>', unsafe_allow_html=True)
    entries = lb.get(key, [])
    if not entries:
        st.caption("No scores yet — be the first!")
        return
    for i, e in enumerate(entries):
        is_new = (highlight_rank == i + 1 and e["name"] == highlight_name)
        row_class = "lb-row lb-row-highlight" if is_new else "lb-row"
        tag = " ← you" if is_new else ""
        st.markdown(
            f'<div class="{row_class}">'
            f'<span class="lb-rank">#{i+1}</span>'
            f'<span class="lb-name">{e["name"]}{tag}</span>'
            f'<span class="lb-time">{format_time(e["time"])}</span>'
            f'<span class="lb-date">{e["date"]}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

def advance_question(next_idx):
    if next_idx >= TOTAL_QUESTIONS:
        raw_elapsed = time.time() - st.session_state.start_time
        elapsed = raw_elapsed + st.session_state.time_penalty   # NEW: add penalties
        st.session_state.elapsed = elapsed
        lb = add_to_leaderboard(st.session_state.player_name, elapsed, st.session_state.mode)
        st.session_state.leaderboard = lb
        st.session_state.new_entry_rank = get_rank(elapsed, st.session_state.mode)
        st.session_state.screen = "result"
    else:
        st.session_state.q_index = next_idx
        if st.session_state.mode == "Multiple Choice":
            na, nb = st.session_state.questions[next_idx]
            opts, _ = make_choices(na, nb)
            st.session_state.mc_options = opts
    st.rerun()

# ── START SCREEN ──────────────────────────────────────────────────────────────
if st.session_state.screen == "start":
    st.title("⏱️ Multiplication Blitz")
    st.markdown("Answer **25 multiplication questions** as fast as you can. Wrong answers keep you on the same question until you get it right.")
    st.markdown("⚠️ **Multiple Choice:** each wrong answer adds a **+5 second penalty** to your final time.")
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
                "penalty_flash": False,   # NEW
                "time_penalty": 0.0,      # NEW
                "screen": "game",
            })
            if mode == "Multiple Choice":
                a, b = questions[0]
                opts, _ = make_choices(a, b)
                st.session_state.mc_options = opts
            st.rerun()

    st.divider()
    with st.expander("🏆 View Leaderboard", expanded=False):
        try:
            lb = load_leaderboard()
            c1, c2 = st.columns(2)
            with c1:
                render_leaderboard(lb, "Type")
            with c2:
                render_leaderboard(lb, "Multiple Choice")
        except Exception:
            st.info("Leaderboard unavailable — check your Supabase connection.")

# ── GAME SCREEN ───────────────────────────────────────────────────────────────
elif st.session_state.screen == "game":
    q_idx = st.session_state.q_index
    a, b = st.session_state.questions[q_idx]
    correct = a * b
    # NEW: display time includes accumulated penalty
    elapsed_now = time.time() - st.session_state.start_time + st.session_state.time_penalty

    st.markdown(f'<div class="timer-display">⏱️ {format_time(elapsed_now)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-label">Question {q_idx + 1} of {TOTAL_QUESTIONS}</div>', unsafe_allow_html=True)
    st.progress(q_idx / TOTAL_QUESTIONS)
    st.markdown(f'<div class="big-problem">{a} × {b} = ?</div>', unsafe_allow_html=True)

    # NEW: penalty flash takes priority and is shown above the wrong flash
    if st.session_state.penalty_flash:
        st.markdown('<div class="flash-penalty">⚠️ +5 SECOND PENALTY!</div>', unsafe_allow_html=True)
        st.session_state.penalty_flash = False
    elif st.session_state.wrong_flash:
        st.markdown('<div class="flash-wrong">✗ Not quite — try again!</div>', unsafe_allow_html=True)
        st.session_state.wrong_flash = False

    if st.session_state.mode == "Type":
        with st.form("answer_form", clear_on_submit=True):
            answer_input = st.number_input("Your answer", step=1, value=0, label_visibility="collapsed")
            submitted = st.form_submit_button("Submit", use_container_width=True, type="primary")
        if submitted:
            if int(answer_input) == correct:
                advance_question(q_idx + 1)
            else:
                st.session_state.wrong_flash = True
                st.rerun()
    else:
        options = st.session_state.mc_options
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if st.button(str(opt), key=f"mc_{opt}_{q_idx}", use_container_width=True):
                    if opt == correct:
                        advance_question(q_idx + 1)
                    else:
                        # NEW: apply penalty and trigger penalty flash
                        st.session_state.time_penalty += MC_PENALTY_SECONDS
                        st.session_state.penalty_flash = True
                        st.rerun()

    # Only auto-rerun (for live timer) in Type mode.
    # MC mode must NOT auto-rerun — it causes duplicate button renders.
    if st.session_state.mode == "Type":
        time.sleep(0.5)
        st.rerun()

# ── RESULT SCREEN ─────────────────────────────────────────────────────────────
elif st.session_state.screen == "result":
    elapsed = st.session_state.elapsed
    rank = st.session_state.new_entry_rank
    mode = st.session_state.mode
    penalty = st.session_state.time_penalty   # NEW

    st.title("🎉 Round Complete!")
    st.markdown(f'<div class="result-time">{format_time(elapsed)}</div>', unsafe_allow_html=True)

    # NEW: show penalty breakdown if any were incurred
    if penalty > 0:
        num_penalties = int(penalty / MC_PENALTY_SECONDS)
        st.markdown(
            f'<div class="result-penalty-note">Includes {num_penalties} × +5s penalty '
            f'({format_time(penalty)} added)</div>',
            unsafe_allow_html=True
        )

    if rank == 1:
        st.markdown('<div class="result-rank">🥇 New #1 all-time! Incredible!</div>', unsafe_allow_html=True)
    elif rank and rank <= 3:
        st.markdown(f'<div class="result-rank">🏅 #{rank} all-time — top of the podium!</div>', unsafe_allow_html=True)
    elif rank and rank <= MAX_LEADERS:
        st.markdown(f'<div class="result-rank">🏆 #{rank} on the leaderboard!</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="result-rank">Keep practicing — the leaderboard awaits!</div>', unsafe_allow_html=True)

    st.divider()
    lb = st.session_state.leaderboard
    if lb:
        c1, c2 = st.columns(2)
        with c1:
            render_leaderboard(lb, "Type", rank if mode == "Type" else None, st.session_state.player_name)
        with c2:
            render_leaderboard(lb, "Multiple Choice", rank if mode == "Multiple Choice" else None, st.session_state.player_name)

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
                "penalty_flash": False,   # NEW
                "time_penalty": 0.0,      # NEW
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
