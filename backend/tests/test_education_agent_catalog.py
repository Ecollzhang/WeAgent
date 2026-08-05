from app.services.agent_service import EDU_SYSTEM_AGENTS


def test_education_agent_catalog_matches_non_programming_mvp_team():
    names = {agent["name"] for agent in EDU_SYSTEM_AGENTS}

    assert {
        "课程设计师",
        "课件制作师",
        "习题生成器",
        "学情分析师",
        "学习规划师",
        "笔记整理师",
        "练习教练",
        "资料研究员",
        "教学审校员",
    } <= names
    prompts = "\n".join(
        f"{agent.get('system_prompt', '')}\n{agent.get('skill', '')}"
        for agent in EDU_SYSTEM_AGENTS
    )
    assert "编程题" not in prompts
