import re

from sqlalchemy import func, or_

from app import db
from app.models.capability import CAPABILITY_TYPES, Capability
from app.models.toolset_category import ToolsetCategory


BUILTIN_TOOLSET_CATEGORIES = [
    {
        "id": "tool_code",
        "name": "代码工具",
        "slug": "tool_code",
        "icon": "el-icon-monitor",
        "color": "#3b82f6",
        "sort_order": 10,
    },
    {
        "id": "tool_file",
        "name": "文件与文档",
        "slug": "tool_file",
        "icon": "el-icon-document",
        "color": "#22c55e",
        "sort_order": 20,
    },
    {
        "id": "tool_web",
        "name": "网络与检索",
        "slug": "tool_web",
        "icon": "el-icon-connection",
        "color": "#8b5cf6",
        "sort_order": 30,
    },
    {
        "id": "tool_data",
        "name": "数据处理",
        "slug": "tool_data",
        "icon": "el-icon-data-analysis",
        "color": "#14b8a6",
        "sort_order": 40,
    },
    {
        "id": "tool_image",
        "name": "图像/多媒体",
        "slug": "tool_image",
        "icon": "el-icon-picture",
        "color": "#ec4899",
        "sort_order": 50,
    },
    {
        "id": "tool_sys",
        "name": "系统与终端",
        "slug": "tool_sys",
        "icon": "el-icon-setting",
        "color": "#f59e0b",
        "sort_order": 60,
    },
    {
        "id": "tool_custom",
        "name": "自定义",
        "slug": "tool_custom",
        "icon": "el-icon-plus",
        "color": "#64748b",
        "sort_order": 999,
    },
]


def _slugify(value):
    text = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", "-", (value or "").strip().lower())
    text = text.strip("-")
    return text or "category"


class ToolsetCategoryService:
    """Category management for the unified toolset UI."""

    def seed_builtin_categories(self):
        changed = False
        for item in BUILTIN_TOOLSET_CATEGORIES:
            category = ToolsetCategory.query.get(item["id"])
            if not category:
                category = ToolsetCategory(
                    id=item["id"],
                    user_id=None,
                    is_builtin=True,
                )
                db.session.add(category)
                changed = True
            for key in ("name", "slug", "icon", "color", "sort_order"):
                if getattr(category, key) != item[key]:
                    setattr(category, key, item[key])
                    changed = True
            if category.is_builtin is not True:
                category.is_builtin = True
                changed = True
        if changed:
            db.session.commit()

    def list_categories(self, user_id):
        self.seed_builtin_categories()
        categories = self._visible_query(user_id).order_by(
            ToolsetCategory.is_builtin.desc(),
            ToolsetCategory.sort_order.asc(),
            ToolsetCategory.created_at.asc(),
        ).all()
        counts = self._counts_by_category(user_id)
        return [self._category_to_dict(item, counts) for item in categories], None

    def create_category(self, user_id, name, icon=None, color=None):
        if not name or not str(name).strip():
            return None, "Category name is required"
        base_slug = _slugify(name)
        category = ToolsetCategory(
            user_id=user_id,
            name=name.strip(),
            slug=self._unique_slug(user_id, base_slug),
            icon=icon or "el-icon-folder",
            color=color or "#4080ff",
            sort_order=self._next_sort_order(user_id),
            is_builtin=False,
        )
        db.session.add(category)
        db.session.commit()
        return self._category_to_dict(category), None

    def update_category(self, user_id, category_id, **kwargs):
        category = ToolsetCategory.query.filter_by(
            id=category_id,
            user_id=user_id,
            is_builtin=False,
        ).first()
        if not category:
            return None, "Category not found"
        if kwargs.get("name") is not None:
            name = str(kwargs["name"]).strip()
            if not name:
                return None, "Category name is required"
            category.name = name
        for key in ("icon", "color"):
            if kwargs.get(key) is not None:
                setattr(category, key, kwargs[key])
        db.session.commit()
        return self._category_to_dict(category), None

    def delete_category(self, user_id, category_id):
        category = ToolsetCategory.query.filter_by(id=category_id).first()
        if not category or (not category.is_builtin and category.user_id != user_id):
            return None, "Category not found"
        if category.is_builtin:
            return None, "Built-in categories cannot be deleted"

        fallback_id = self.resolve_category_id(user_id, category_id="tool_custom")
        Capability.query.filter_by(
            user_id=user_id,
            category_id=category.id,
        ).update({"category_id": fallback_id})
        db.session.delete(category)
        db.session.commit()
        return {"deleted": True, "reassigned_to": fallback_id}, None

    def resolve_category_id(self, user_id, category_id=None, category_slug=None,
                            fallback_slug="tool_custom"):
        self.seed_builtin_categories()
        value = category_id or category_slug
        if value:
            category = self._visible_query(user_id).filter(
                or_(ToolsetCategory.id == value, ToolsetCategory.slug == value)
            ).first()
            if not category:
                raise ValueError("Category not found")
            return category.id

        fallback = self._visible_query(user_id).filter(
            or_(ToolsetCategory.id == fallback_slug, ToolsetCategory.slug == fallback_slug)
        ).first()
        return fallback.id if fallback else None

    def _visible_query(self, user_id):
        return ToolsetCategory.query.filter(
            (ToolsetCategory.is_builtin == True) | (ToolsetCategory.user_id == user_id)
        )

    def _counts_by_category(self, user_id):
        rows = db.session.query(
            Capability.category_id,
            Capability.type,
            func.count(Capability.id),
        ).filter(
            (Capability.is_builtin == True) | (Capability.user_id == user_id),
            Capability.source != "archived",
        ).group_by(Capability.category_id, Capability.type).all()
        counts = {}
        for category_id, capability_type, count in rows:
            if not category_id:
                continue
            counts.setdefault(category_id, self._empty_counts())
            counts[category_id][capability_type] = int(count)
        return counts

    def _empty_counts(self):
        return {capability_type: 0 for capability_type in CAPABILITY_TYPES}

    def _category_to_dict(self, category, counts=None):
        data = category.to_dict()
        data["counts"] = (counts or {}).get(category.id, self._empty_counts())
        return data

    def _unique_slug(self, user_id, base_slug):
        slug = base_slug
        suffix = 2
        while self._visible_query(user_id).filter(ToolsetCategory.slug == slug).first():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    def _next_sort_order(self, user_id):
        max_order = db.session.query(func.max(ToolsetCategory.sort_order)).filter_by(
            user_id=user_id,
            is_builtin=False,
        ).scalar()
        return int(max_order or 1000) + 10


toolset_category_service = ToolsetCategoryService()
