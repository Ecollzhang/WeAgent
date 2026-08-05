"""Seed system document templates for a new office service."""
from extensions import db
from models.document_template import DocumentTemplate


SYSTEM_TEMPLATES = [
    ('会议通知', 'notice', '# {{会议主题}}\n\n各有关人员：\n\n现定于 {{会议时间}} 召开 {{会议主题}}，请准时参加。\n\n会议议程：\n{{会议议程}}'),
    ('会议纪要', 'minutes', '# {{会议主题}}会议纪要\n\n时间：{{会议时间}}\n\n参会人员：{{参会人员}}\n\n## 会议决议\n{{决议事项}}\n\n## 行动项\n{{行动项}}'),
    ('工作推进通知', 'notice', '# 关于推进 {{事项名称}} 的通知\n\n各相关人员：\n\n为落实有关安排，现将工作要求通知如下：\n\n{{工作要求}}'),
    ('阶段验收通知', 'notice', '# 关于开展 {{项目名称}} 阶段验收的通知\n\n各小组：\n\n请于 {{截止时间}} 前完成验收材料提交。\n\n特此通知。'),
    ('跨组协同通知', 'notice', '# 关于 {{事项名称}} 跨组协同安排的通知\n\n相关小组：\n\n请按职责分工推进，并在 {{时间节点}} 前反馈进展。'),
    ('工作周报', 'report', '# {{周期}}工作周报\n\n## 本周进展\n{{本周进展}}\n\n## 风险与问题\n{{风险问题}}\n\n## 下周计划\n{{下周计划}}'),
    ('请假申请', 'request', '# 请假申请\n\n申请人：{{申请人}}\n请假时间：{{开始时间}} 至 {{结束时间}}\n事由：{{请假事由}}\n\n请审批。'),
    ('报销申请', 'request', '# 报销申请\n\n申请人：{{申请人}}\n报销金额：{{报销金额}}\n费用说明：{{费用说明}}\n\n请审批。'),
    ('采购申请', 'request', '# 采购申请\n\n申请部门：{{申请部门}}\n采购事项：{{采购事项}}\n预算金额：{{预算金额}}\n采购理由：{{采购理由}}\n\n请审批。'),
]


def seed_system_templates():
    """Create built-in templates without touching custom user templates."""
    created = False
    for name, document_type, content in SYSTEM_TEMPLATES:
        if DocumentTemplate.query.filter_by(name=name, is_system=True).first():
            continue
        db.session.add(DocumentTemplate(
            name=name,
            document_type=document_type,
            content=content,
            format_spec='请根据单位公文规范补全标题、称谓和落款。',
            is_system=True,
        ))
        created = True
    if created:
        db.session.commit()
