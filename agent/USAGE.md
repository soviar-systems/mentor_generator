## How Your Learning System Works

I will generate **one file** for you:

1. **mentor_system_prompt** — Contains everything: the mentor's personality, teaching rules, your profile, learning curriculum, and the session record format. This is your mentor's complete instruction set.

You will also create one more file yourself:

2. **course_history** — An initially empty file where you will accumulate all your session records. After each session, you append the new record here.

### Learning Workflow

**When you start your FIRST learning session:**

1. Open a **new chat** with your AI (Gemini, Claude, DeepSeek, etc.)
2. Attach one file: **mentor_system_prompt**
3. Say 'Let's start' or simply greet your mentor
4. The mentor will introduce itself, present your learning roadmap, and begin Phase 1

**When you start SUBSEQUENT learning sessions (session 2, 3, ...):**

1. Open a **new chat** with your AI
2. Paste the **mentor_system_prompt** text into the web chat message box
3. Attach **course_history** file and any additional context files (previous session notes, exercises you have done, etc.)
4. Say 'Let's continue' or greet your mentor
5. The mentor will recap where you left off and continue from there

**When a session ends:**

A session can end in several ways:

- **You decide to stop** — tell the mentor (e.g., 'Let's wrap up for today')
- **A topic or phase is completed** — the mentor may suggest a natural stopping point
- **The conversation gets very long** — wrap up the session to preserve progress.

In all cases:

1. The mentor will output a new session record
2. Append this record to your **course_history** file
3. Never delete old records from course_history

### Updating Your Profile

Your **mentor_system_prompt** contains a `user_profile` section with your learning data. After sessions, the session record includes observations about your learning patterns and difficulties. You can *optionally* update `learning_style_observed` and `known_difficulties` in your profile based on these.

You can also edit other profile fields if your circumstances change (new hardware, different learning strategy, etc.). **You won't break anything** as long as you only change the values after colons. Keep a backup copy.

### Why New Chats?

AI chats have context limits. Starting fresh with files gives full context without clutter.

### Why One course_history File?

Most web AI chats limit how many files you can attach. This keeps you at 1-2 files total.

### File Format

YAML format, but convertible to JSON or Markdown. Structure matters, not format.
