from services.edu.product_agent_runs import (
    build_product_prompt,
    product_template,
    product_workflow,
)
from services.edu.workflow_models import product_business_route


class Course:
    id = "course-1"
    title = "高中英语阅读"
    subject_code = "high_school_english"
    grade_band = "senior_high"


def test_question_and_paper_agent_products_only_write_drafts():
    question = product_workflow("question_generation")
    paper = product_workflow("paper_generation")
    assert question["role"] == "teacher"
    assert question["tools"] == [
        "edu.course.context.get",
        "edu.knowledge.search",
        "edu.question_bank.upsert",
    ]
    assert paper["tools"] == ["edu.question_bank.search", "edu.paper.compose"]
    question_prompt = build_product_prompt(
        "question_generation",
        Course(),
        {"question_count": 8, "difficulty": "medium", "knowledge_points": ["情感推断"]},
    )
    assert "education_questions_from_agent_reply" in question_prompt
    assert '"questions"' in question_prompt
    assert "Do not call education_action" in question_prompt
    paper_prompt = build_product_prompt(
        "paper_generation",
        Course(),
        {"title": "阅读诊断", "question_count": 5, "duration_minutes": 30},
    )
    assert "education_paper_from_agent_reply" in paper_prompt
    assert '"question_count"' in paper_prompt
    assert "Do not call education_action" in paper_prompt
    question_node = next(
        node
        for node in product_template("question_generation")["nodes"]
        if node["agent_role"] == "exercise_generator"
    )
    paper_node = next(
        node
        for node in product_template("paper_generation")["nodes"]
        if node["agent_role"] == "exercise_generator"
    )
    assert question_node["finalizer"] == {
        "type": "education_questions_from_agent_reply"
    }
    assert paper_node["finalizer"] == {
        "type": "education_paper_from_agent_reply"
    }


def test_knowledge_research_product_uses_search_fetch_and_adoption_tools():
    contract = product_workflow("knowledge_research")
    assert contract["tools"] == [
        "edu.web.research",
        "edu.knowledge.resource.adopt",
    ]
    route = product_business_route("knowledge_research", "course-1")
    assert route["path"].endswith("/knowledge")
    prompt = build_product_prompt(
        "knowledge_research",
        Course(),
        {
            "query": "narrative reading evidence",
            "license_note": "CC BY-SA 4.0",
        },
    )
    assert "education_knowledge_from_agent_reply" in prompt
    assert "Do not call education_action" in prompt
    node = next(
        node
        for node in product_template("knowledge_research")["nodes"]
        if node["agent_role"] == "research_worker"
    )
    assert node["finalizer"] == {
        "type": "education_knowledge_from_agent_reply"
    }
