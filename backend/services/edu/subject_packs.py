"""Versioned MVP subject-pack manifests."""

SUBJECT_PACKS = [
    {
        "schema_version": "1.0",
        "version": "primary-chinese-mvp.1",
        "subject_code": "primary_chinese",
        "grade_band": "primary",
        "learning_domains": ["reading", "writing", "integrated"],
        "themes": [
            "growth_character",
            "family",
            "nature_life",
            "traditional_culture",
            "science_discovery",
            "fairy_tale_imagination",
        ],
        "lesson_plan_sections": [
            "learning_objectives",
            "text_and_class_profile",
            "key_points",
            "reading_activities",
            "writing_transfer",
            "assessment",
            "homework",
            "teacher_reflection",
        ],
        "text_genres": {
            "narrative": {
                "teaching_focus": ["event_sequence", "character_evidence", "emotion_change"],
                "suggested_activities": ["timeline", "retelling", "character_card", "imitative_writing"],
            },
            "scenery": {
                "teaching_focus": ["observation_order", "sensory_language", "scene_emotion"],
                "suggested_activities": ["keyword_marking", "sensory_table", "scene_paragraph"],
            },
            "expository_science": {
                "teaching_focus": ["key_information", "object_features", "explanation_methods"],
                "suggested_activities": ["information_card", "structure_map", "plain_language_rewrite"],
            },
            "poetry_classical": {
                "teaching_focus": ["rhythm_recitation", "imagery", "context_and_emotion"],
                "suggested_activities": ["annotated_recitation", "imagery_map", "creative_rewriting"],
            },
            "fable_fairy_tale": {
                "teaching_focus": ["plot_pattern", "imagination", "moral_with_evidence"],
                "suggested_activities": ["role_reading", "plot_map", "alternative_ending"],
            },
        },
        "fallback_policy": [
            "exact_genre_lesson_type",
            "genre_generic",
            "learning_domain_generic",
            "subject_generic",
        ],
    },
    {
        "schema_version": "1.0",
        "version": "high-school-english-mvp.1",
        "subject_code": "high_school_english",
        "grade_band": "senior_high",
        "learning_domains": ["reading", "writing", "integrated"],
        "themes": [
            "people_and_self",
            "people_and_society",
            "people_and_nature",
            "culture_and_communication",
            "science_and_technology",
        ],
        "lesson_plan_sections": [
            "learning_objectives",
            "discourse_and_learner_analysis",
            "language_and_thinking_focus",
            "pre_while_post_reading",
            "reading_to_write_transfer",
            "formative_assessment",
            "assignment",
            "teacher_reflection",
        ],
        "text_genres": {
            "narrative": {
                "teaching_focus": ["plot", "point_of_view", "characterization", "theme_evidence"],
                "suggested_activities": ["story_arc", "evidence_table", "continuation_writing"],
            },
            "expository": {
                "teaching_focus": ["main_idea", "text_structure", "evidence", "academic_vocabulary"],
                "suggested_activities": ["structure_mapping", "summary", "explanatory_paragraph"],
            },
            "argumentative": {
                "teaching_focus": ["claim", "reasoning", "evidence_quality", "counterargument"],
                "suggested_activities": ["claim_evidence_map", "source_comparison", "argument_writing"],
            },
            "practical": {
                "teaching_focus": ["audience", "purpose", "register", "genre_conventions"],
                "suggested_activities": ["model_analysis", "language_bank", "email_or_notice_writing"],
            },
        },
        "fallback_policy": [
            "exact_genre_lesson_type",
            "genre_generic",
            "learning_domain_generic",
            "subject_generic",
        ],
    },
]


AGENT_ROLES = [
    {"code": "course_designer", "side": "teacher", "outputs": ["lesson_plan_json"]},
    {"code": "courseware_maker", "side": "teacher", "outputs": ["slide_document_json", "html"]},
    {"code": "exercise_generator", "side": "teacher", "outputs": ["assessment_json", "rubric_json"]},
    {"code": "learning_analyst", "side": "teacher", "outputs": ["learning_report_json"]},
    {"code": "learning_planner", "side": "student", "outputs": ["learning_plan_json"]},
    {"code": "note_organizer", "side": "student", "outputs": ["rich_document_json", "knowledge_cards"]},
    {"code": "practice_coach", "side": "student", "outputs": ["practice_feedback_json"]},
    {"code": "research_worker", "side": "internal", "outputs": ["ranked_sources"]},
    {"code": "teaching_reviewer", "side": "internal", "outputs": ["validation_report"]},
]


def _nodes(*roles, approval=True):
    nodes = [
        {"id": f"step-{index}", "type": "agent_task", "agent_role": role}
        for index, role in enumerate(roles, 1)
    ]
    if approval:
        nodes.append({"id": "teacher-approval", "type": "approval", "gate": "teacher_publish"})
    return nodes


WORKFLOW_TEMPLATES = [
    ("teacher_lesson_preparation", "教师备课全流程", _nodes("research_worker", "course_designer", "courseware_maker", "exercise_generator", "teaching_reviewer")),
    ("reading_lesson", "阅读课设计", _nodes("course_designer", "exercise_generator", "teaching_reviewer")),
    ("writing_lesson", "写作课设计", _nodes("course_designer", "exercise_generator", "teaching_reviewer")),
    ("reading_to_writing", "阅读—写作整合课", _nodes("research_worker", "course_designer", "courseware_maker", "exercise_generator", "teaching_reviewer")),
    ("assessment_publish", "习题生成与发布", _nodes("exercise_generator", "teaching_reviewer")),
    ("writing_feedback", "作文批改与反馈", _nodes("practice_coach", "teaching_reviewer", approval=False)),
    ("post_lesson_analytics", "课后学情分析", _nodes("learning_analyst", approval=False)),
    ("student_diagnosis_plan", "学生诊断与学习规划", _nodes("learning_planner", "practice_coach", approval=False)),
]
WORKFLOW_TEMPLATES = [
    {
        "code": code,
        "name": name,
        "schema_version": "1.0",
        "execution_mode": "guided",
        "scope": "system",
        "nodes": nodes,
        "required_approval_gates": [
            node["gate"] for node in nodes if node["type"] == "approval"
        ],
    }
    for code, name, nodes in WORKFLOW_TEMPLATES
]
