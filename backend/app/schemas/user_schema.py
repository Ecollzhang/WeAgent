from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    """Registration request schema."""
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))


class LoginSchema(Schema):
    """Login request schema."""
    username = fields.String(required=True)
    password = fields.String(required=True)


class UserResponseSchema(Schema):
    """User response schema."""
    id = fields.String()
    username = fields.String()
    email = fields.String()
    avatar_url = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
