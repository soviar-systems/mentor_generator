{
  "_template_notes": {
    "purpose": "User profile and curriculum - fill during meta-prompt generation",
    "usage": "User data. Attach to every session along with mentor_system_prompt. Can be updated if circumstances change (hardware, learning strategy, etc.).",
    "sharing": "The mentor_system_prompt can be shared across users; each user has their own user_profile with their profile and curriculum.",
    "format": "JSON shown here, but content can be converted to YAML, Markdown, or plain text as needed"
  },

  "metadata": {
    "course_id": "<generated_unique_id>",
    "created": "<generation_date>",
    "topic": "<USER_TOPIC>"
  },

  "user_profile": {
    "user_language": "<user preferred language for learning>",
    "initial_assessment": {
      "level": "<beginner/intermediate/advanced>",
      "description": "<meta_prompt assessment of user's starting point>"
    },
    "professional_skills": ["<relevant existing skills>"],
    "learning_goals": ["<user stated goals>"],
    "depth_preference": "<overview/intermediate/expert/hands-on>"
  },

  "environment_and_strategy": {
      "available_resources": "<tools, equipment, software, or physical spaces the user has access to>",
      "constraints": "<any limitations like budget, physical space, health, or hardware limits>",
      "efficiency_principles": "Focus on approaches working within stated resources and constraints",

      "pacing": {
        "choice": "<DEPTH-FIRST or TIME-BOXED>",
        "user_time_input": "<raw time input from question_7>",
        "policy": {
          "DEPTH-FIRST": "Depth over speed. Progression gated solely by verified mastery. Time input determines session length.",
          "TIME-BOXED": "Time is primary gate. Content depth/validation secondary to meeting deadline."
        }
      }
    },

  "curriculum": {
    "_notes": "Staged learning progression. Mentor follows this structure but mastery gates actual advancement.",
    "phases": [
      {
        "phase_number": 1,
        "title": "<Phase 1 title>",
        "focus": "<what this phase covers>",
        "topics": [
          "<topic 1>",
          "<topic 2>",
          "<topic 3>"
        ],
        "hands_on": "<practical component if any>",
        "estimated_sessions": "<rough estimate, mastery determines actual>"
      },
      {
        "phase_number": 2,
        "title": "<Phase 2 title>",
        "focus": "<what this phase covers>",
        "topics": [
          "<topic 1>",
          "<topic 2>"
        ],
        "hands_on": "<practical component if any>",
        "estimated_sessions": "<rough estimate>"
      }
    ],
    "subtopics_requested": ["<specific subtopics user wants covered>"]
  }
}
