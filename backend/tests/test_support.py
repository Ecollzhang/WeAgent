import sys
import types


class _ExtensionStub:
    def __init__(self, *args, **kwargs):
        pass

    def init_app(self, *args, **kwargs):
        pass


def stub_flask_extensions():
    extensions = {
        "flask_sqlalchemy": ("SQLAlchemy",),
        "flask_migrate": ("Migrate",),
        "flask_jwt_extended": ("JWTManager",),
        "flask_cors": ("CORS",),
        "flask_socketio": ("SocketIO",),
    }

    for module_name, class_names in extensions.items():
        if module_name in sys.modules:
            continue
        module = types.ModuleType(module_name)
        for class_name in class_names:
            setattr(module, class_name, _ExtensionStub)
        sys.modules[module_name] = module
