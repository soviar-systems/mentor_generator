{
  "_template_notes": {
    "purpose": "Session record template - defines the format for session records in course_history",
    "usage": "The mentor uses this template structure to create a session record at the end of each session. The user appends the record to their course_history file.",
    "immutability": "Never modify existing session records in course_history. Only append new records."
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
