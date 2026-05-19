"""
Azure SDK integration helpers for live inventory and cost dashboards.

The module imports Azure SDK packages lazily so the workbook dashboard can still
load with a helpful setup message if the Azure dependencies are not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd


DEFAULT_AZURE_CONFIG_FILE = "azure_config.env"


@dataclass(frozen=True)
class AzureConnectionConfig:
    tenant_id: str
    application_id: str
    object_id: str = ""
    client_secret: str = ""
    subscription_ids: Tuple[str, ...] = ()

    @property
    def auth_mode(self) -> str:
        if self.client_secret:
            return "Service principal"
        if self.application_id:
            return "Managed identity"
        return "Default credential"


def load_azure_environment_config(config_path: str = DEFAULT_AZURE_CONFIG_FILE) -> Dict[str, str]:
    """Load non-secret Azure connection defaults from a simple KEY=VALUE file.

    Existing process environment variables win over file values so deployment
    platforms can still override the bundled config safely.
    """
    path = Path(config_path)
    loaded = {}
    if not path.exists():
        return loaded

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded


def parse_subscription_ids(raw_value: str) -> Tuple[str, ...]:
    if not raw_value:
        return ()
    values = []
    for chunk in raw_value.replace("\n", ",").split(","):
        value = chunk.strip()
        if value:
            values.append(value)
    return tuple(dict.fromkeys(values))


def azure_sdk_status() -> Tuple[bool, str]:
    try:
        import azure.identity  # noqa: F401
        import azure.mgmt.costmanagement  # noqa: F401
        import azure.mgmt.resourcegraph  # noqa: F401
        import azure.mgmt.subscription  # noqa: F401
    except ImportError as exc:
        return False, str(exc)
    return True, ""


def build_credential(config: AzureConnectionConfig):
    try:
        from azure.identity import ClientSecretCredential, DefaultAzureCredential, ManagedIdentityCredential
    except ImportError as exc:
        raise RuntimeError(
            "Azure SDK packages are not installed. Run `pip install -r requirements.txt` "
            "or rebuild the Docker image."
        ) from exc

    if config.client_secret:
        if not config.tenant_id or not config.application_id:
            raise ValueError("Tenant ID and Application ID are required with a client secret.")
        return ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.application_id,
            client_secret=config.client_secret,
        )

    if config.application_id:
        return ManagedIdentityCredential(client_id=config.application_id)

    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


class AzureApiDataClient:
    def __init__(self, config: AzureConnectionConfig):
        self.config = config
        self.credential = build_credential(config)

    def list_subscriptions(self) -> pd.DataFrame:
        from azure.mgmt.subscription import SubscriptionClient

        client = SubscriptionClient(self.credential)
        rows = []
        allowed = set(self.config.subscription_ids)
        for subscription in client.subscriptions.list():
            subscription_id = getattr(subscription, "subscription_id", "")
            if allowed and subscription_id not in allowed:
                continue
            rows.append(
                {
                    "subscription_id": subscription_id,
                    "subscription_name": getattr(subscription, "display_name", ""),
                    "state": str(getattr(subscription, "state", "")),
                    "tenant_id": self.config.tenant_id,
                }
            )
        return pd.DataFrame(rows)

    def query_inventory(self, subscription_ids: Iterable[str]) -> pd.DataFrame:
        from azure.mgmt.resourcegraph import ResourceGraphClient
        from azure.mgmt.resourcegraph.models import QueryRequest

        subscriptions = list(subscription_ids)
        if not subscriptions:
            return pd.DataFrame()

        query = """
Resources
| project
    resource_id = id,
    resource_name = name,
    resource_type = type,
    resource_group = resourceGroup,
    location,
    subscription_id = subscriptionId,
    tags,
    kind,
    sku
| order by subscription_id asc, resource_group asc, resource_name asc
"""
        client = ResourceGraphClient(self.credential)
        result = client.resources(QueryRequest(subscriptions=subscriptions, query=query))
        data = getattr(result, "data", []) or []
        inventory = pd.DataFrame(data)
        if inventory.empty:
            return inventory

        inventory["service_category"] = inventory["resource_type"].map(service_category)
        inventory["resource_type_friendly"] = inventory["resource_type"].map(friendly_resource_type)
        inventory["owner"] = inventory["tags"].map(extract_owner_from_tags)
        inventory["tag_count"] = inventory["tags"].map(lambda value: len(value) if isinstance(value, dict) else 0)
        return inventory

    def query_costs(self, subscription_ids: Iterable[str], days: int = 30) -> pd.DataFrame:
        from azure.mgmt.costmanagement import CostManagementClient
        from azure.mgmt.costmanagement.models import (
            QueryAggregation,
            QueryDataset,
            QueryDefinition,
            QueryGrouping,
            QueryTimePeriod,
        )

        subscriptions = list(subscription_ids)
        if not subscriptions:
            return pd.DataFrame()

        client = CostManagementClient(self.credential)
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        rows = []

        for subscription_id in subscriptions:
            scope = f"/subscriptions/{subscription_id}"
            parameters = QueryDefinition(
                type="ActualCost",
                timeframe="Custom",
                time_period=QueryTimePeriod(from_property=start_date, to=end_date),
                dataset=QueryDataset(
                    granularity="Daily",
                    aggregation={"totalCost": QueryAggregation(name="PreTaxCost", function="Sum")},
                    grouping=[
                        QueryGrouping(type="Dimension", name="ServiceName"),
                        QueryGrouping(type="Dimension", name="ResourceGroupName"),
                    ],
                ),
            )
            try:
                result = client.query.usage(scope=scope, parameters=parameters)
            except Exception as exc:  # Keep partial dashboards usable if one subscription lacks cost access.
                rows.append(
                    {
                        "subscription_id": subscription_id,
                        "date": "",
                        "service_name": "Cost query failed",
                        "resource_group": "",
                        "cost": 0.0,
                        "currency": "",
                        "error": str(exc),
                    }
                )
                continue

            columns = [column.name for column in getattr(result, "columns", [])]
            for raw_row in getattr(result, "rows", []) or []:
                row = dict(zip(columns, raw_row))
                rows.append(normalize_cost_row(subscription_id, row))

        return pd.DataFrame(rows)

    def load_inventory_and_costs(self, cost_days: int = 30) -> Dict[str, pd.DataFrame]:
        subscriptions = self.list_subscriptions()
        subscription_ids = subscriptions["subscription_id"].dropna().tolist() if not subscriptions.empty else []
        inventory = self.query_inventory(subscription_ids)
        costs = self.query_costs(subscription_ids, days=cost_days)
        return {
            "subscriptions": subscriptions,
            "inventory": inventory,
            "costs": costs,
        }


def normalize_cost_row(subscription_id: str, row: Dict[str, object]) -> Dict[str, object]:
    return {
        "subscription_id": subscription_id,
        "date": row.get("UsageDate") or row.get("Date") or "",
        "service_name": row.get("ServiceName") or "Unknown",
        "resource_group": row.get("ResourceGroupName") or "Unknown",
        "cost": float(row.get("PreTaxCost") or row.get("Cost") or 0),
        "currency": row.get("Currency") or "",
        "error": "",
    }


def extract_owner_from_tags(tags) -> str:
    if not isinstance(tags, dict):
        return "Missing owner tag"
    for key in ("Owner", "owner", "PIC", "pic", "ApplicationOwner", "BusinessOwner"):
        value = tags.get(key)
        if value:
            return str(value)
    return "Missing owner tag"


def friendly_resource_type(resource_type: object) -> str:
    text = str(resource_type or "").lower()
    if not text:
        return "Unknown"
    overrides = {
        "microsoft.compute/virtualmachines": "Virtual Machines",
        "microsoft.storage/storageaccounts": "Storage Accounts",
        "microsoft.network/networksecuritygroups": "Network Security Groups",
        "microsoft.network/virtualnetworks": "Virtual Networks",
        "microsoft.web/sites": "App Services",
        "microsoft.sql/servers/databases": "SQL Databases",
        "microsoft.recoveryservices/vaults": "Recovery Services Vaults",
    }
    if text in overrides:
        return overrides[text]
    return text.split("/")[-1].replace("-", " ").replace("_", " ").title()


def service_category(resource_type: object) -> str:
    text = str(resource_type or "").lower()
    rules = [
        ("compute", "Compute"),
        ("network", "Network"),
        ("storage", "Storage"),
        ("sql", "Database"),
        ("documentdb", "Database"),
        ("insights", "Monitoring"),
        ("operationalinsights", "Monitoring"),
        ("recoveryservices", "Backup"),
        ("web/sites", "App Services"),
        ("eventhub", "Messaging"),
        ("keyvault", "Security"),
    ]
    for needle, category in rules:
        if needle in text:
            return category
    return "Other"
