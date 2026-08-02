"""ServiceSpec — 微服务自描述数据模型.

每个领域服务（rd / rag / edu / office）通过 /api/{service}/spec 暴露自身能力。
此模块定义标准化的 dataclass，供各服务导入使用，确保格式统一。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ServiceEndpoint:
    """单个 API 端点描述."""
    method: str                          # GET / POST / PUT / PATCH / DELETE
    path: str                            # /api/{service}/xxx
    description: str                     # 一句话描述
    params: Optional[dict] = None        # query 参数说明  {key: {type, required, description}}
    body: Optional[dict] = None          # request body 说明  {key: {type, required, description}}


@dataclass
class ServiceCapability:
    """面向 LLM 的服务能力摘要."""
    name: str                            # 能力名称，如"需求管理"
    description: str                     # 一句话描述


@dataclass
class ServiceSpec:
    """服务自描述规格."""

    service: str                                              # 服务名: rd / rag / edu / office
    version: str                                              # 语义版本号
    description: str                                          # 一句话描述
    base_url: str                                             # 服务 base URL
    status: str = "healthy"                                   # healthy / degraded / unavailable
    capabilities: list[ServiceCapability] = field(default_factory=list)
    popular_endpoints: list[ServiceEndpoint] = field(default_factory=list)
    all_endpoints: list[ServiceEndpoint] = field(default_factory=list)

    # ── 序列化 ──────────────────────────────────────────

    @staticmethod
    def _endpoint_to_dict(ep: ServiceEndpoint) -> dict:
        d = {
            "method": ep.method,
            "path": ep.path,
            "description": ep.description,
        }
        if ep.params:
            d["params"] = ep.params
        if ep.body:
            d["body"] = ep.body
        return d

    @staticmethod
    def _capability_to_dict(cap: ServiceCapability) -> dict:
        return {"name": cap.name, "description": cap.description}

    def to_dict(self) -> dict:
        """序列化为 API 响应 JSON."""
        return {
            "service": self.service,
            "version": self.version,
            "description": self.description,
            "base_url": self.base_url,
            "status": self.status,
            "capabilities": [self._capability_to_dict(c) for c in self.capabilities],
            "popular_endpoints": [self._endpoint_to_dict(e) for e in self.popular_endpoints],
            "all_endpoints": [self._endpoint_to_dict(e) for e in self.all_endpoints],
        }

    # ── 反序列化 ──────────────────────────────────────────

    @staticmethod
    def _endpoint_from_dict(data: dict) -> ServiceEndpoint:
        return ServiceEndpoint(
            method=data["method"],
            path=data["path"],
            description=data["description"],
            params=data.get("params"),
            body=data.get("body"),
        )

    @staticmethod
    def _capability_from_dict(data: dict) -> ServiceCapability:
        return ServiceCapability(
            name=data["name"],
            description=data["description"],
        )

    @staticmethod
    def from_dict(data: dict) -> "ServiceSpec":
        """从 JSON 反序列化."""
        return ServiceSpec(
            service=data["service"],
            version=data["version"],
            description=data["description"],
            base_url=data["base_url"],
            status=data.get("status", "healthy"),
            capabilities=[ServiceSpec._capability_from_dict(c) for c in data.get("capabilities", [])],
            popular_endpoints=[ServiceSpec._endpoint_from_dict(e) for e in data.get("popular_endpoints", [])],
            all_endpoints=[ServiceSpec._endpoint_from_dict(e) for e in data.get("all_endpoints", [])],
        )


# ── 服务注册表（各服务 base URL） ──────────────────────────

SERVICE_REGISTRY = {
    "rag":    "http://host.docker.internal:5104",
    "rd":     "http://host.docker.internal:5101",
    "edu":    "http://host.docker.internal:5102",
    "office": "http://host.docker.internal:5103",
}
