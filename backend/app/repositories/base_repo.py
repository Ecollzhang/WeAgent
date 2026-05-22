from app import db


class BaseRepository:
    """Generic CRUD repository."""

    def __init__(self, model):
        self.model = model

    def get_by_id(self, id):
        """Get record by primary key."""
        return self.model.query.get(id)

    def get_all(self, **filters):
        """Get all records with optional filters."""
        query = self.model.query
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        return query.all()

    def create(self, **kwargs):
        """Create a new record."""
        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    def update(self, instance, **kwargs):
        """Update an existing record."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    def delete(self, instance):
        """Delete a record."""
        db.session.delete(instance)
        db.session.commit()

    def paginate(self, page=1, per_page=20, **filters):
        """Paginated query with optional filters."""
        query = self.model.query
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        query = query.order_by(self.model.created_at.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)
