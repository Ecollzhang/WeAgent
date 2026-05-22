from flask import jsonify


def success_response(data=None, message='success', code=200):
    """Unified success response."""
    response = {
        'code': code,
        'message': message,
        'data': data
    }
    return jsonify(response), code


def error_response(message='error', code=400, data=None):
    """Unified error response."""
    response = {
        'code': code,
        'message': message,
        'data': data
    }
    return jsonify(response), code


def paginate_response(query, page, per_page, schema=None, many=True):
    """Paginated response helper."""
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items

    if schema:
        data = schema.dump(items, many=many)
    else:
        data = [item.to_dict() for item in items]

    return success_response({
        'items': data,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
    })
