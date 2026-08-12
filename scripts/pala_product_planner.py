"""Validation boundary for host-AI product planning candidates."""

from __future__ import annotations

from dataclasses import dataclass

from pala_dependencies import validate_dependency_graph
from pala_product import ProductSpec


def _records(payload: dict[str, object], name: str, required: set[str]) -> list[dict[str, object]]:
    value = payload.get(name)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    records: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"invalid {name} record")
        if any(not isinstance(item[field], str) or not item[field].strip() for field in required):
            raise ValueError(f"invalid {name} text")
        records.append(dict(item))
    return records


def _graph(payload: dict[str, object], name: str) -> dict[str, dict[str, object]]:
    value = payload.get(name)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty graph")
    graph: dict[str, dict[str, object]] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(item, dict):
            raise ValueError(f"invalid {name} node")
        dependencies = item.get("dependencies")
        if not isinstance(dependencies, list) or any(
            not isinstance(dep, str) or not dep.strip() for dep in dependencies
        ):
            raise ValueError(f"invalid {name} dependencies")
        graph[key] = dict(item)
    report = validate_dependency_graph(graph)
    if report["status"] != "passed":
        raise ValueError(f"invalid {name}: {report['errors']}")
    return graph


@dataclass(frozen=True)
class ProductPlan:
    product_spec: ProductSpec
    acceptance_matrix: list[dict[str, object]]
    environment_requirements: list[dict[str, object]]
    milestone_graph: dict[str, dict[str, object]]
    task_dag: dict[str, dict[str, object]]
    status: str = "passed"


def validate_plan(payload: dict[str, object]) -> ProductPlan:
    """Validate a provider candidate; never fill unknown facts from guesses."""
    spec_payload = payload.get("product_spec")
    if not isinstance(spec_payload, dict):
        raise ValueError("product_spec is required")
    return ProductPlan(
        product_spec=ProductSpec.from_dict(spec_payload),
        acceptance_matrix=_records(payload, "acceptance_matrix", {"id", "criterion", "evidence"}),
        environment_requirements=_records(
            payload, "environment_requirements", {"id", "capability", "status"}
        ),
        milestone_graph=_graph(payload, "milestone_graph"),
        task_dag=_graph(payload, "task_dag"),
    )
