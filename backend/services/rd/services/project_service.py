"""项目业务逻辑."""
from database import db
from models.project import RdProject
from models.project_file import RdProjectFile


class ProjectService:
    """研发项目 CRUD + 文件管理."""

    # ── 项目 CRUD ────────────────────────────────────────

    def list_projects(self, user_id, workspace_id=None):
        """获取用户的项目列表，支持按工作空间筛选."""
        q = RdProject.query.filter_by(user_id=user_id, status='active')
        if workspace_id:
            q = q.filter_by(workspace_id=workspace_id)
        return [p.to_dict() for p in q.order_by(RdProject.updated_at.desc()).all()]

    def get_project(self, project_id, user_id=None):
        """获取项目详情（含文件列表）."""
        q = RdProject.query.filter_by(id=project_id)
        if user_id:
            q = q.filter_by(user_id=user_id)
        project = q.first()
        if not project:
            return None
        return project.to_dict(include_files=True)

    def create_project(self, user_id, data):
        """创建新项目."""
        project = RdProject(
            workspace_id=data.get('workspace_id', ''),
            user_id=user_id,
            name=data['name'].strip(),
            description=data.get('description', '').strip() or None,
            cover_url=data.get('cover_url', '').strip() or None,
            tech_stack=data.get('tech_stack', {}),
            coding_standards=data.get('coding_standards', '').strip() or None,
            visibility=data.get('visibility', 'team'),
        )
        db.session.add(project)
        db.session.commit()
        return project.to_dict(include_files=True)

    def update_project(self, project_id, user_id, data):
        """更新项目信息."""
        project = RdProject.query.filter_by(id=project_id, user_id=user_id).first()
        if not project:
            return None

        if 'name' in data:
            project.name = data['name'].strip()
        if 'description' in data:
            project.description = data['description'].strip() or None
        if 'cover_url' in data:
            project.cover_url = data['cover_url'].strip() or None
        if 'tech_stack' in data:
            project.tech_stack = data['tech_stack']
        if 'coding_standards' in data:
            project.coding_standards = data['coding_standards'].strip() or None
        if 'status' in data:
            project.status = data['status']
        if 'visibility' in data:
            project.visibility = data['visibility']

        db.session.commit()
        return project.to_dict(include_files=True)

    # ── 甘特图数据 ──

    def get_gantt_data(self, project_id, user_id=None):
        """获取甘特图数据：迭代和需求的起止日期."""
        project = RdProject.query.filter_by(id=project_id)
        if user_id:
            project = project.filter_by(user_id=user_id)
        project = project.first()
        if not project:
            return None

        from models.iteration import RdIteration
        from models.requirement import RdRequirement

        iterations = RdIteration.query.filter_by(project_id=project_id) \
            .order_by(RdIteration.sort_order.asc()).all()
        reqs = RdRequirement.query.filter_by(project_id=project_id) \
            .filter(RdRequirement.start_date.isnot(None)) \
            .order_by(RdRequirement.start_date.asc()).all()

        return {
            'iterations': [
                {
                    'id': i.id, 'name': i.name,
                    'start_date': i.start_date.isoformat() if i.start_date else None,
                    'end_date': i.end_date.isoformat() if i.end_date else None,
                    'status': i.status, 'sort_order': i.sort_order,
                }
                for i in iterations
            ],
            'requirements': [
                {
                    'id': r.id, 'title': r.title,
                    'iteration_id': r.iteration_id,
                    'start_date': r.start_date.isoformat() if r.start_date else None,
                    'due_date': r.due_date.isoformat() if r.due_date else None,
                    'status': r.status, 'priority': r.priority,
                }
                for r in reqs
            ],
        }

    def delete_project(self, project_id, user_id):
        """删除项目（硬删除，级联删除所有关联数据）."""
        project = RdProject.query.filter_by(id=project_id, user_id=user_id).first()
        if not project:
            return False
        db.session.delete(project)
        db.session.commit()
        return True

    # ── 项目文件管理 ──────────────────────────────────────

    def list_files(self, project_id, user_id=None):
        """获取项目文件列表."""
        project = RdProject.query.filter_by(id=project_id)
        if user_id:
            project = project.filter_by(user_id=user_id)
        project = project.first()
        if not project:
            return None
        return [f.to_dict() for f in project.files.order_by('file_path').all()]

    def get_file(self, file_id, user_id=None):
        """获取文件内容."""
        q = RdProjectFile.query.filter_by(id=file_id)
        if user_id:
            q = q.join(RdProject).filter(RdProject.user_id == user_id)
        f = q.first()
        if not f:
            return None
        data = f.to_dict()
        data['content'] = f.content or ''
        return data

    def add_file(self, project_id, user_id, data):
        """向项目添加文件."""
        project = RdProject.query.filter_by(id=project_id, user_id=user_id).first()
        if not project:
            return None

        f = RdProjectFile(
            project_id=project_id,
            conversation_id=data.get('conversation_id'),
            file_name=data['file_name'],
            file_path=data.get('file_path', data['file_name']),
            content=data.get('content', ''),
            file_type=data.get('file_type', ''),
            size=data.get('size', len(data.get('content', ''))),
        )
        db.session.add(f)
        db.session.commit()
        return f.to_dict()

    def delete_file(self, file_id, user_id):
        """删除文件."""
        q = RdProjectFile.query.filter_by(id=file_id)
        if user_id:
            q = q.join(RdProject).filter(RdProject.user_id == user_id)
        f = q.first()
        if not f:
            return False
        db.session.delete(f)
        db.session.commit()
        return True

    # ── 项目上下文（用于 Agent 感知对话）──────────────────

    def get_project_context(self, project_id, user_id=None):
        """获取项目上下文信息，供 Agent 系统提示词注入."""
        project = RdProject.query.filter_by(id=project_id)
        if user_id:
            project = project.filter_by(user_id=user_id)
        project = project.first()
        if not project:
            return None

        tech = project.tech_stack or {}
        files = [f.file_path for f in project.files.order_by('file_path').all()]

        return {
            'project_name': project.name,
            'description': project.description or '',
            'tech_stack': {
                'frontend': tech.get('frontend', '未指定'),
                'backend': tech.get('backend', '未指定'),
                'database': tech.get('database', '未指定'),
                'deployment': tech.get('deployment', '未指定'),
            },
            'files': files,
            'file_count': len(files),
        }


# 模块级单例
project_service = ProjectService()
