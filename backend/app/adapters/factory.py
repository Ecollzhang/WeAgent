class AgentAdapterFactory:
    _providers = {}

    @classmethod
    def register(cls, name, adapter_class):
        cls._providers[name.lower()] = adapter_class
        return adapter_class

    @classmethod
    def create(cls, name, **kwargs):
        adapter_class = cls.get(name)
        return adapter_class(**kwargs)

    @classmethod
    def get(cls, name):
        adapter_class = cls._providers.get(name.lower())
        if not adapter_class:
            raise ValueError(f"Unknown adapter: {name}")
        return adapter_class

    @classmethod
    def providers(cls):
        return sorted(cls._providers)
