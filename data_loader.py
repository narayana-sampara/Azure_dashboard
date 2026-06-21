"""
Manager-friendly Azure inventory data layer.

Azure Resource Graph is the primary source. This module adapts live inventory
and normalizes the fallback workbook into the same canonical dashboard fields.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


DEFAULT_EXCEL_FILE = "file/All_Resources_Inventory 1.xlsx"
UNKNOWN_OWNER = "Unassigned / unclear"
FRONT_FACING_SHEETS = {"Dashboard", "Inventory", "Ownership", "Data Dictionary"}


SERVICE_CATEGORY_RULES = [
    ("compute", "Compute"),
    ("virtualmachines", "Compute"),
    ("disks", "Compute"),
    ("sshpublickeys", "Compute"),
    ("network", "Network"),
    ("virtualnetworks", "Network"),
    ("networksecuritygroups", "Network"),
    ("publicipaddresses", "Network"),
    ("networkinterfaces", "Network"),
    ("route", "Network"),
    ("storage", "Storage"),
    ("storageaccounts", "Storage"),
    ("sql", "Database"),
    ("database", "Database"),
    ("elastic", "Database"),
    ("insights", "Monitoring"),
    ("datacollection", "Monitoring"),
    ("workbooks", "Monitoring"),
    ("operationalinsights", "Monitoring"),
    ("recoveryservices", "Backup"),
    ("backup", "Backup"),
    ("vpn", "Connectivity"),
    ("expressroute", "Connectivity"),
    ("bastion", "Connectivity"),
    ("localnetworkgateways", "Connectivity"),
    ("eventhub", "Messaging"),
    ("event hubs", "Messaging"),
    ("web/sites", "App Services"),
]


FRIENDLY_TYPE_OVERRIDES = {
    "microsoft.compute/virtualmachines": "Virtual Machines",
    "microsoft.compute/virtualmachines/extensions": "VM Extensions",
    "microsoft.compute/disks": "Managed Disks",
    "microsoft.compute/snapshots": "Snapshots",
    "microsoft.network/networksecuritygroups": "Network Security Groups",
    "microsoft.network/networkinterfaces": "Network Interfaces",
    "microsoft.network/publicipaddresses": "Public IP Addresses",
    "microsoft.network/virtualnetworks": "Virtual Networks",
    "microsoft.storage/storageaccounts": "Storage Accounts",
    "microsoft.insights/datacollectionrules": "Data Collection Rules",
    "microsoft.insights/scheduledqueryrules": "Scheduled Query Rules",
    "microsoft.operationsmanagement/solutions": "Operations Management Solutions",
    "microsoft.recoveryservices/vaults": "Recovery Services Vaults",
    "microsoft.web/sites": "App Services",
}


@dataclass(frozen=True)
class FieldMap:
    canonical: str
    candidates: Iterable[str]


FIELD_MAPS = [
    FieldMap("resource_name", ["resourcename", "resource", "vmname", "name", "storagename", "storageaccountname"]),
    FieldMap("raw_resource_type", ["resourcetype", "type", "resource type", "app type"]),
    FieldMap("resource_group", ["resourcegroup", "resource group", "vnetresourcegroup"]),
    FieldMap("location", ["location"]),
    FieldMap("subscription_id", ["subscriptionid", "subscription id"]),
    FieldMap("subscription_name", ["subscriptionname", "subscription"]),
    FieldMap("owner", ["pic", "pic's", "owner"]),
    FieldMap("status", ["status", "connectionstatus", "tunnelstatus", "ama_status"]),
]


def _clean_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _column_key(column: object) -> str:
    text = _clean_text(column).lower()
    return "".join(ch for ch in text if ch.isalnum())


def _normalize_resource_type(raw_type: object) -> str:
    raw = _clean_text(raw_type)
    if not raw:
        return "Unknown"

    lowered = raw.lower()
    if lowered in FRIENDLY_TYPE_OVERRIDES:
        return FRIENDLY_TYPE_OVERRIDES[lowered]

    tail = lowered.split("/")[-1]
    words = tail.replace("-", " ").replace("_", " ").split()
    if not words:
        return raw
    return " ".join(word.capitalize() for word in words)


def _service_category(raw_type: object, source_sheet: str = "") -> str:
    haystack = f"{_clean_text(raw_type)} {source_sheet}".lower().replace(" ", "")
    for needle, category in SERVICE_CATEGORY_RULES:
        if needle.replace(" ", "") in haystack:
            return category
    return "Other"


def _readable_sheet_category(sheet_name: str) -> str:
    return _service_category("", sheet_name)


class AzureInventoryDataManager:
    """Adapts live Azure or workbook data into manager-friendly dataframes."""

    def __init__(self, excel_file: str = DEFAULT_EXCEL_FILE):
        self.excel_file = Path(excel_file)
        self.sheets_data: Dict[str, pd.DataFrame] = {}
        self.sheet_names: List[str] = []
        self.source_sheet_names: List[str] = []
        self.inventory = pd.DataFrame()

    def load_all_sheets(self) -> Dict[str, pd.DataFrame]:
        if not self.excel_file.exists():
            raise FileNotFoundError(f"Workbook not found: {self.excel_file}")

        xls = pd.ExcelFile(self.excel_file)
        self.sheet_names = xls.sheet_names
        self.source_sheet_names = [
            sheet_name for sheet_name in self.sheet_names
            if sheet_name not in FRONT_FACING_SHEETS
        ]
        self.sheets_data = {}

        for sheet_name in self.sheet_names:
            df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
            self.sheets_data[sheet_name] = self._drop_blank_columns(df)
            logger.info("Loaded %s: %s rows x %s columns", sheet_name, len(df), len(df.columns))

        self.inventory = self._build_inventory()
        return self.sheets_data

    def load_azure_inventory(
        self,
        inventory: pd.DataFrame,
        subscriptions: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Populate the manager from live Azure Resource Graph data."""
        resources = inventory.copy()
        if resources.empty:
            raise ValueError("Azure Resource Graph returned no resources.")

        if subscriptions is not None and not subscriptions.empty and "subscription_id" in resources.columns:
            subscription_columns = [
                column for column in ("subscription_id", "subscription_name")
                if column in subscriptions.columns
            ]
            if len(subscription_columns) == 2 and "subscription_name" not in resources.columns:
                resources = resources.merge(
                    subscriptions[subscription_columns].drop_duplicates("subscription_id"),
                    on="subscription_id",
                    how="left",
                )

        resources["raw_resource_type"] = resources.get("resource_type", "")
        if "resource_type_friendly" in resources.columns:
            resources["resource_type"] = resources["resource_type_friendly"]
        else:
            resources["resource_type"] = resources["raw_resource_type"].map(_normalize_resource_type)
        if "service_category" not in resources.columns:
            resources["service_category"] = resources["raw_resource_type"].map(_service_category)
        if "owner" not in resources.columns:
            resources["owner"] = UNKNOWN_OWNER
        resources["owner"] = (
            resources["owner"]
            .replace({"": UNKNOWN_OWNER, "Missing owner tag": UNKNOWN_OWNER})
            .fillna(UNKNOWN_OWNER)
        )
        resources["status"] = "Not reported"
        resources["source_sheet"] = "Azure Resource Graph"
        if "subscription_name" not in resources.columns:
            resources["subscription_name"] = "Unknown"
        resources["subscription_name"] = resources["subscription_name"].replace("", "Unknown").fillna("Unknown")

        required_text_columns = ("resource_name", "resource_group", "location", "subscription_id")
        for column in required_text_columns:
            if column not in resources.columns:
                resources[column] = ""

        self.inventory = resources
        self.sheet_names = ["Azure Resource Graph"]
        self.source_sheet_names = ["Azure Resource Graph"]
        self.sheets_data = {"Azure Resource Graph": resources.copy()}

        raw_types = resources["raw_resource_type"].fillna("").astype(str).str.lower()
        live_views = {
            "Virtual Machine": raw_types.eq("microsoft.compute/virtualmachines"),
            "StorageAccounts": raw_types.eq("microsoft.storage/storageaccounts"),
            "NSG": raw_types.eq("microsoft.network/networksecuritygroups"),
            "All_Vnets_Subnets_Prefix": raw_types.eq("microsoft.network/virtualnetworks"),
        }
        for name, mask in live_views.items():
            self.sheets_data[name] = resources.loc[mask].copy()
        return self.inventory

    def _drop_blank_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        usable_columns = [
            col for col in df.columns
            if not str(col).startswith("Unnamed") and _clean_text(col)
        ]
        return df.loc[:, usable_columns].copy()

    def _find_column(self, df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
        candidate_keys = {_column_key(candidate) for candidate in candidates}
        for column in df.columns:
            if _column_key(column) in candidate_keys:
                return column
        return None

    def normalize_sheet(self, sheet_name: str) -> pd.DataFrame:
        df = self.sheets_data.get(sheet_name, pd.DataFrame()).copy()
        normalized = pd.DataFrame(index=df.index)

        for field in FIELD_MAPS:
            column = self._find_column(df, field.candidates)
            normalized[field.canonical] = df[column].map(_clean_text) if column else ""

        if "raw_resource_type" not in normalized or normalized["raw_resource_type"].eq("").all():
            normalized["raw_resource_type"] = sheet_name

        normalized["source_sheet"] = sheet_name
        normalized["resource_type"] = normalized["raw_resource_type"].map(_normalize_resource_type)
        normalized["service_category"] = [
            _service_category(raw_type, sheet_name)
            for raw_type in normalized["raw_resource_type"]
        ]
        normalized["owner"] = normalized["owner"].replace("", UNKNOWN_OWNER)
        normalized["status"] = normalized["status"].replace("", "Not reported")
        return normalized

    def _build_inventory(self) -> pd.DataFrame:
        resources = self.normalize_sheet("Resources") if "Resources" in self.sheets_data else pd.DataFrame()
        if resources.empty:
            return resources

        ownership = self._ownership_lookup()
        if not ownership.empty:
            resources = resources.merge(
                ownership,
                on=["subscription_id", "resource_name"],
                how="left",
                suffixes=("", "_lookup"),
            )
            resources["owner"] = resources["owner_lookup"].combine_first(resources["owner"])
            resources["subscription_name"] = resources["subscription_name_lookup"].combine_first(
                resources["subscription_name"]
            )
            resources = resources.drop(columns=["owner_lookup", "subscription_name_lookup"])

        resources["owner"] = resources["owner"].replace("", UNKNOWN_OWNER).fillna(UNKNOWN_OWNER)
        resources["subscription_name"] = resources["subscription_name"].replace("", "Unknown").fillna("Unknown")
        return resources

    def _ownership_lookup(self) -> pd.DataFrame:
        if "PIC" not in self.sheets_data:
            return pd.DataFrame(columns=["subscription_id", "resource_name", "owner", "subscription_name"])

        pic = self.normalize_sheet("PIC")
        lookup = pic[["subscription_id", "resource_name", "owner", "subscription_name"]].copy()
        lookup = lookup[(lookup["subscription_id"] != "") & (lookup["resource_name"] != "")]
        lookup = lookup.drop_duplicates(["subscription_id", "resource_name"], keep="first")
        return lookup

    def get_filtered_inventory(
        self,
        subscription: str = "All",
        resource_group: str = "All",
        category: str = "All",
        owner: str = "All",
        location: str = "All",
    ) -> pd.DataFrame:
        df = self.inventory.copy()
        filters = {
            "subscription_name": subscription,
            "resource_group": resource_group,
            "service_category": category,
            "owner": owner,
            "location": location,
        }
        for column, selected in filters.items():
            if selected != "All" and column in df.columns:
                df = df[df[column] == selected]
        return df

    def search_inventory(self, df: pd.DataFrame, search_term: str) -> pd.DataFrame:
        if not search_term:
            return df
        mask = df.astype(str).apply(
            lambda col: col.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        return df[mask]

    def get_resource_statistics(self) -> Dict[str, object]:
        inventory = self.inventory
        assigned = int((inventory["owner"] != UNKNOWN_OWNER).sum()) if not inventory.empty else 0
        return {
            "total_sheets": len(self.sheet_names),
            "source_sheets": len(self.source_sheet_names),
            "total_resources": len(inventory),
            "subscriptions": inventory["subscription_id"].nunique() if not inventory.empty else 0,
            "resource_groups": inventory["resource_group"].nunique() if not inventory.empty else 0,
            "locations": inventory["location"].nunique() if not inventory.empty else 0,
            "resource_types": inventory["resource_type"].nunique() if not inventory.empty else 0,
            "assigned_owner_count": assigned,
            "ownership_coverage": assigned / len(inventory) if len(inventory) else 0,
        }

    def summary_by(self, column: str, limit: Optional[int] = None) -> pd.DataFrame:
        if self.inventory.empty or column not in self.inventory.columns:
            return pd.DataFrame(columns=[column, "count"])
        summary = (
            self.inventory[column]
            .replace("", "Unknown")
            .fillna("Unknown")
            .value_counts()
            .rename_axis(column)
            .reset_index(name="count")
        )
        return summary.head(limit) if limit else summary

    def owner_summary(self) -> pd.DataFrame:
        if self.inventory.empty:
            return pd.DataFrame(columns=["owner", "resources", "resource_groups", "subscriptions"])
        return (
            self.inventory.groupby("owner", dropna=False)
            .agg(
                resources=("resource_name", "count"),
                resource_groups=("resource_group", "nunique"),
                subscriptions=("subscription_id", "nunique"),
            )
            .reset_index()
            .sort_values("resources", ascending=False)
        )

    def workbook_summary(self) -> pd.DataFrame:
        rows = []
        for sheet_name in self.source_sheet_names:
            df = self.sheets_data[sheet_name]
            rows.append(
                {
                    "Sheet": sheet_name,
                    "Rows": len(df),
                    "Columns": len(df.columns),
                    "Service Group": _readable_sheet_category(sheet_name),
                }
            )
        return pd.DataFrame(rows)

    def vm_status_summary(self) -> pd.DataFrame:
        if "Virtual Machine" not in self.sheets_data:
            return pd.DataFrame(columns=["status", "count"])
        vm = self.normalize_sheet("Virtual Machine")
        return vm["status"].replace("", "Not reported").value_counts().rename_axis("status").reset_index(name="count")

    def storage_security_summary(self) -> pd.DataFrame:
        if "StorageAccounts" not in self.sheets_data:
            return pd.DataFrame(columns=["Check", "Pass", "Fail"])

        storage = self.sheets_data["StorageAccounts"].copy()
        checks = []
        definitions = {
            "HTTPS only": "SupportsHttpsTrafficOnly",
            "Secure transfer required": "SecureTransferRequired",
            "Blob public access disabled": "AllowBlobPublicAccess",
            "Anonymous blob access disabled": "AllowBlobAnonymousAccess",
            "Encryption enabled": "EncryptionEnabled",
        }
        for label, column in definitions.items():
            if column not in storage.columns:
                continue
            values = storage[column].fillna(False)
            if "disabled" in label:
                passed = (~values.astype(bool)).sum()
            else:
                passed = values.astype(bool).sum()
            checks.append({"Check": label, "Pass": int(passed), "Fail": int(len(storage) - passed)})
        return pd.DataFrame(checks)

    def monitoring_summary(self) -> pd.DataFrame:
        if "Virtual Machine" not in self.sheets_data:
            return pd.DataFrame(columns=["Signal", "Covered", "Missing"])

        vm = self.sheets_data["Virtual Machine"].copy()
        rows = []
        if "AMA_Status" in vm.columns:
            installed = vm["AMA_Status"].astype(str).str.contains("Installed", case=False, na=False)
            rows.append({"Signal": "Azure Monitor Agent", "Covered": int(installed.sum()), "Missing": int((~installed).sum())})
        if "LAW" in vm.columns:
            covered = vm["LAW"].map(_clean_text) != ""
            rows.append({"Signal": "Log Analytics Workspace", "Covered": int(covered.sum()), "Missing": int((~covered).sum())})
        if "DCR" in vm.columns:
            covered = vm["DCR"].map(_clean_text) != ""
            rows.append({"Signal": "Data Collection Rule", "Covered": int(covered.sum()), "Missing": int((~covered).sum())})
        return pd.DataFrame(rows)

    def exportable_inventory(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        source = self.inventory if df is None else df
        columns = [
            "resource_name",
            "resource_type",
            "raw_resource_type",
            "service_category",
            "resource_group",
            "location",
            "subscription_name",
            "subscription_id",
            "owner",
            "status",
            "source_sheet",
        ]
        return source[[column for column in columns if column in source.columns]].copy()


def initialize_data_manager(excel_file: str = DEFAULT_EXCEL_FILE) -> AzureInventoryDataManager:
    manager = AzureInventoryDataManager(excel_file)
    manager.load_all_sheets()
    return manager


def initialize_data_manager_from_azure(
    inventory: pd.DataFrame,
    subscriptions: Optional[pd.DataFrame] = None,
) -> AzureInventoryDataManager:
    manager = AzureInventoryDataManager()
    manager.load_azure_inventory(inventory, subscriptions)
    return manager
