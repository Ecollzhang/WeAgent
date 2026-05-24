from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.utils.response import success_response, error_response
from app.schemas.deploy_schema import CreateDeploySchema
from app.services.deploy_service import deploy_service
from marshmallow import ValidationError

deploy_bp = Blueprint('deploys', __name__)


@deploy_bp.route('', methods=['POST'])
@jwt_required()
def create_deploy():
    try:
        schema = CreateDeploySchema()
        data = schema.load(request.json)
    except ValidationError as e:
        return error_response(str(e.messages), code=400)

    result, error = deploy_service.create(
        conversation_id=data['conversation_id'],
        artifact_id=data.get('artifact_id'),
        source_type=data.get('source_type', 'webpage'),
    )
    if error:
        return error_response(error, code=400)
    return success_response(result, message='Deployment started', code=201)


@deploy_bp.route('/<deploy_id>', methods=['GET'])
@jwt_required()
def get_deploy(deploy_id):
    result, error = deploy_service.get_by_id(deploy_id)
    if error:
        return error_response(error, code=404)
    return success_response(result)


@deploy_bp.route('/conversation/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation_deploys(conversation_id):
    result, error = deploy_service.get_by_conversation(conversation_id)
    if error:
        return error_response(error, code=400)
    return success_response(result)
