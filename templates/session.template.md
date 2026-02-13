{
  "_template_notes": {
    "purpose": "Session record template - mentor fills this at end of each session",
    "usage": "Save as session_N (session_1, session_2...). Attach ALL session files to each new chat.",
    "immutability": "Never modify old session files. Each session creates a new file."
  },

  "session_number": "<increment from last session, or 1>",
  "timestamp": "<ISO datetime>",
  "duration_approx": "<estimated session length>",

  "position": {
    "phase": "<current phase from curriculum>",
    "topic_covered": "<main topic(s) this session>",
    "next_topic": "<what comes next>",
    "phase_progress": "<X of Y topics in current phase>"
  },

  "content": {
    "session_summary": "<2-3 sentence summary>",
    "tasks_completed": ["<exercises, problems, or challenges the user solved>"],
    "projects_worked_on": ["<any project work done this session>"],
    "resources_suggested": [
      {"topic": "<topic>", "resource": "<title>", "type": "<book/video/article>"}
    ]
  },

  "mastery": {
    "concepts_validated": ["<concepts user demonstrated understanding of>"],
    "concepts_struggling": ["<concepts needing more work>"],
    "validation_method": "<how mastery was verified>"
  },

  "observations": {
    "learning_patterns": ["<observations about how this user learns best>"],
    "user_problems": ["<difficulties encountered, confusion points, frustrations>"],
    "mentor_failures": [
      {
        "error": "<what the mentor got wrong>",
        "context": "<when/where it occurred>",
        "lesson": "<what to avoid in future>"
      }
    ]
  },

  "mentor_notes": "<notes for future sessions>"
}
