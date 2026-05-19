"""
Simplified Azure Inventory Dashboard.

Designed for managers and Azure operations teams who need quick portfolio,
ownership, operational, and searchable inventory views.
"""

from __future__ import annotations

from io import BytesIO
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from azure_api import (
    AzureApiDataClient,
    AzureConnectionConfig,
    azure_sdk_status,
    load_azure_environment_config,
    parse_subscription_ids,
)
from data_loader import UNKNOWN_OWNER, initialize_data_manager


load_azure_environment_config()


st.set_page_config(
    page_title="Azure Inventory Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d8dee9;
        border-radius: 8px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.9rem;
        color: #4b5563;
    }
    .section-note {
        color: #4b5563;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_data_manager():
    return initialize_data_manager()


def safe_chart(df: pd.DataFrame, chart_factory, empty_message: str):
    if df.empty:
        st.info(empty_message)
        return
    st.plotly_chart(chart_factory(df), width='stretch')


def filtered_inventory(dm):
    inventory = dm.inventory
    st.sidebar.header("Filters")

    def options(column: str):
        values = sorted(value for value in inventory[column].dropna().unique().tolist() if value)
        return ["All"] + values

    selected_subscription = st.sidebar.selectbox("Subscription", options("subscription_name"))
    selected_group = st.sidebar.selectbox("Resource group", options("resource_group"))
    selected_category = st.sidebar.selectbox("Service group", options("service_category"))
    selected_owner = st.sidebar.selectbox("Owner / PIC", options("owner"))
    selected_location = st.sidebar.selectbox("Location", options("location"))

    return dm.get_filtered_inventory(
        subscription=selected_subscription,
        resource_group=selected_group,
        category=selected_category,
        owner=selected_owner,
        location=selected_location,
    )


def download_buttons(dm, df: pd.DataFrame, prefix: str):
    export_df = dm.exportable_inventory(df)
    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv,
        file_name=f"{prefix}.csv",
        mime="text/csv",
    )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name="Inventory", index=False)
    buffer.seek(0)
    st.download_button(
        "Download Excel",
        data=buffer,
        file_name=f"{prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def dataframe_download_buttons(df: pd.DataFrame, prefix: str, sheet_name: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv,
        file_name=f"{prefix}.csv",
        mime="text/csv",
    )

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    buffer.seek(0)
    st.download_button(
        "Download Excel",
        data=buffer,
        file_name=f"{prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@st.cache_data(show_spinner=False, ttl=1800)
def load_azure_data(
    tenant_id: str,
    application_id: str,
    object_id: str,
    client_secret: str,
    subscription_ids: tuple[str, ...],
    cost_days: int,
):
    config = AzureConnectionConfig(
        tenant_id=tenant_id,
        application_id=application_id,
        object_id=object_id,
        client_secret=client_secret,
        subscription_ids=subscription_ids,
    )
    client = AzureApiDataClient(config)
    return client.load_inventory_and_costs(cost_days=cost_days)


def render_azure_api_page():
    st.header("Azure API Dashboards")
    st.markdown(
        '<div class="section-note">Connect to Azure APIs to build live subscription-level and resource-level dashboards for inventory and cost.</div>',
        unsafe_allow_html=True,
    )

    sdk_ready, sdk_error = azure_sdk_status()
    if not sdk_ready:
        st.warning(
            "Azure SDK packages are not installed in this environment. "
            "Install dependencies with `pip install -r requirements.txt` or rebuild the Docker image."
        )
        st.code(sdk_error)
        return

    with st.expander("Azure connectivity configuration", expanded=True):
        st.caption(
            "Use Application ID as the client ID. Object ID is recorded for clarity but Azure authentication uses "
            "Application ID plus either managed identity or a client secret."
        )
        cfg_col1, cfg_col2 = st.columns(2)
        with cfg_col1:
            tenant_id = st.text_input("Tenant ID", value=os.getenv("AZURE_TENANT_ID", ""))
            application_id = st.text_input(
                "Application ID / Client ID",
                value=os.getenv("AZURE_CLIENT_ID", ""),
            )
            object_id = st.text_input("Object ID", value=os.getenv("AZURE_OBJECT_ID", ""))
        with cfg_col2:
            client_secret = st.text_input(
                "Client secret (optional)",
                value=os.getenv("AZURE_CLIENT_SECRET", ""),
                type="password",
                help="If blank, the page uses managed identity with the Application ID as client ID.",
            )
            subscription_ids_raw = st.text_area(
                "Subscription IDs (optional allowlist)",
                value=os.getenv("AZURE_SUBSCRIPTION_IDS", ""),
                help="Comma-separated or one per line. Leave blank to use all subscriptions visible to the identity.",
            )
            cost_days = st.slider("Cost lookback days", min_value=7, max_value=90, value=30, step=1)

        subscription_ids = parse_subscription_ids(subscription_ids_raw)
        auth_mode = "Service principal" if client_secret else "Managed identity"
        st.info(f"Authentication mode: {auth_mode}. Cached refresh TTL: 30 minutes.")

    load_clicked = st.button("Refresh Azure API data", type="primary")
    if load_clicked:
        load_azure_data.clear()

    if not load_clicked and "azure_api_data_loaded" not in st.session_state:
        st.info("Enter Azure configuration, then click **Refresh Azure API data**.")
        return

    if not tenant_id and client_secret:
        st.error("Tenant ID is required when using a client secret.")
        return
    if not application_id and (client_secret or auth_mode == "Managed identity"):
        st.error("Application ID / Client ID is required for this Azure API connection.")
        return

    with st.spinner("Querying Azure subscriptions, inventory, and cost data..."):
        try:
            azure_data = load_azure_data(
                tenant_id=tenant_id,
                application_id=application_id,
                object_id=object_id,
                client_secret=client_secret,
                subscription_ids=subscription_ids,
                cost_days=cost_days,
            )
            st.session_state["azure_api_data_loaded"] = True
        except Exception as exc:
            st.error(f"Azure API refresh failed: {exc}")
            return

    subscriptions = azure_data.get("subscriptions", pd.DataFrame())
    inventory = azure_data.get("inventory", pd.DataFrame())
    costs = azure_data.get("costs", pd.DataFrame())

    if subscriptions.empty:
        st.warning("No readable subscriptions were returned for this Azure identity.")
        return

    tab_inventory, tab_cost = st.tabs(["Azure Inventory", "Azure Cost"])

    with tab_inventory:
        render_azure_inventory_dashboard(subscriptions, inventory)

    with tab_cost:
        render_azure_cost_dashboard(subscriptions, costs)


def render_azure_inventory_dashboard(subscriptions: pd.DataFrame, inventory: pd.DataFrame):
    st.subheader("Azure Inventory")
    if inventory.empty:
        st.info("No Azure resources were returned by Resource Graph for the selected subscriptions.")
        st.dataframe(subscriptions, width='stretch', hide_index=True)
        return

    subscription_names = subscriptions.set_index("subscription_id")["subscription_name"].to_dict()
    inventory = inventory.copy()
    inventory["subscription_name"] = inventory["subscription_id"].map(subscription_names).fillna(inventory["subscription_id"])

    filter_cols = st.columns(4)
    selected_subscription = filter_cols[0].selectbox(
        "Subscription",
        ["All"] + sorted(inventory["subscription_name"].dropna().unique().tolist()),
        key="azure_inventory_subscription",
    )
    selected_group = filter_cols[1].selectbox(
        "Resource group",
        ["All"] + sorted(inventory["resource_group"].dropna().unique().tolist()),
        key="azure_inventory_group",
    )
    selected_category = filter_cols[2].selectbox(
        "Service group",
        ["All"] + sorted(inventory["service_category"].dropna().unique().tolist()),
        key="azure_inventory_category",
    )
    search_term = filter_cols[3].text_input("Search", key="azure_inventory_search")

    filtered = inventory.copy()
    if selected_subscription != "All":
        filtered = filtered[filtered["subscription_name"] == selected_subscription]
    if selected_group != "All":
        filtered = filtered[filtered["resource_group"] == selected_group]
    if selected_category != "All":
        filtered = filtered[filtered["service_category"] == selected_category]
    if search_term:
        mask = filtered.astype(str).apply(
            lambda column: column.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        filtered = filtered[mask]

    metric_cols = st.columns(5)
    metric_cols[0].metric("Resources", f"{len(filtered):,}")
    metric_cols[1].metric("Subscriptions", f"{filtered['subscription_id'].nunique():,}")
    metric_cols[2].metric("Resource groups", f"{filtered['resource_group'].nunique():,}")
    metric_cols[3].metric("Locations", f"{filtered['location'].nunique():,}")
    owner_coverage = (filtered["owner"] != "Missing owner tag").sum() / len(filtered) if len(filtered) else 0
    metric_cols[4].metric("Owner tag coverage", f"{owner_coverage:.0%}")

    chart_cols = st.columns(2)
    with chart_cols[0]:
        type_counts = filtered["resource_type_friendly"].value_counts().head(12).rename_axis("Resource type").reset_index(name="Count")
        safe_chart(
            type_counts,
            lambda data: px.pie(data, values="Count", names="Resource type", title="Resource Types Distribution"),
            "No resource type data is available.",
        )
    with chart_cols[1]:
        category_counts = filtered["service_category"].value_counts().rename_axis("Service group").reset_index(name="Count")
        safe_chart(
            category_counts,
            lambda data: px.sunburst(data, values="Count", names="Service group", title="Service Groups Distribution"),
            "No service group data is available.",
        )

    display_columns = [
        "subscription_name",
        "resource_name",
        "resource_type_friendly",
        "service_category",
        "resource_group",
        "location",
        "owner",
        "resource_id",
    ]
    st.dataframe(
        filtered[[column for column in display_columns if column in filtered.columns]],
        width='stretch',
        hide_index=True,
        height=460,
    )
    dataframe_download_buttons(filtered, "azure_api_inventory", "AzureInventory")


def render_azure_cost_dashboard(subscriptions: pd.DataFrame, costs: pd.DataFrame):
    st.subheader("Azure Cost")
    if costs.empty:
        st.info("No Cost Management data was returned for the selected subscriptions.")
        return

    subscription_names = subscriptions.set_index("subscription_id")["subscription_name"].to_dict()
    costs = costs.copy()
    costs["subscription_name"] = costs["subscription_id"].map(subscription_names).fillna(costs["subscription_id"])

    errors = costs[costs.get("error", "") != ""] if "error" in costs.columns else pd.DataFrame()
    usable_costs = costs[costs.get("error", "") == ""] if "error" in costs.columns else costs

    if not errors.empty:
        st.warning("Some subscriptions could not return cost data. See failed rows in the table below.")

    if usable_costs.empty:
        st.dataframe(costs, width='stretch', hide_index=True)
        return

    filter_cols = st.columns(3)
    selected_subscription = filter_cols[0].selectbox(
        "Subscription",
        ["All"] + sorted(usable_costs["subscription_name"].dropna().unique().tolist()),
        key="azure_cost_subscription",
    )
    selected_service = filter_cols[1].selectbox(
        "Service",
        ["All"] + sorted(usable_costs["service_name"].dropna().unique().tolist()),
        key="azure_cost_service",
    )
    selected_group = filter_cols[2].selectbox(
        "Resource group",
        ["All"] + sorted(usable_costs["resource_group"].dropna().unique().tolist()),
        key="azure_cost_group",
    )

    filtered = usable_costs.copy()
    if selected_subscription != "All":
        filtered = filtered[filtered["subscription_name"] == selected_subscription]
    if selected_service != "All":
        filtered = filtered[filtered["service_name"] == selected_service]
    if selected_group != "All":
        filtered = filtered[filtered["resource_group"] == selected_group]

    total_cost = filtered["cost"].sum()
    currency = next((value for value in filtered["currency"].dropna().unique().tolist() if value), "")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total cost", f"{total_cost:,.2f} {currency}".strip())
    metric_cols[1].metric("Subscriptions", f"{filtered['subscription_id'].nunique():,}")
    metric_cols[2].metric("Services", f"{filtered['service_name'].nunique():,}")
    metric_cols[3].metric("Resource groups", f"{filtered['resource_group'].nunique():,}")

    chart_cols = st.columns(2)
    with chart_cols[0]:
        service_cost = filtered.groupby("service_name", as_index=False)["cost"].sum().sort_values("cost", ascending=False).head(10)
        safe_chart(
            service_cost,
            lambda data: px.sunburst(data, values="cost", names="service_name", title="Service Cost Distribution"),
            "No service cost data is available.",
        )
    with chart_cols[1]:
        group_cost = filtered.groupby("resource_group", as_index=False)["cost"].sum().sort_values("cost", ascending=False).head(12)
        safe_chart(
            group_cost,
            lambda data: px.treemap(data, values="cost", labels="resource_group", title="Cost by Resource Group"),
            "No resource group cost data is available.",
        )

    daily_cost = filtered.groupby("date", as_index=False)["cost"].sum().sort_values("date")
    safe_chart(
        daily_cost,
        lambda data: px.line(data, x="date", y="cost", markers=True, labels={"date": "Date", "cost": "Cost"}),
        "No daily cost trend is available.",
    )

    st.dataframe(filtered, width='stretch', hide_index=True, height=420)
    dataframe_download_buttons(filtered, "azure_api_cost", "AzureCost")


try:
    dm = load_data_manager()
except Exception as exc:
    st.error(f"Unable to load the Azure inventory workbook: {exc}")
    st.stop()

if dm.inventory.empty:
    st.warning("No Resources sheet was found in the workbook.")
    st.stop()

st.title("Azure Inventory Dashboard")
st.caption("Manager-friendly view of resources, ownership, operations, and searchable inventory.")

if st.sidebar.button("Refresh workbook data"):
    st.cache_resource.clear()
    st.rerun()

page = st.sidebar.radio(
    "View",
    ["Overview", "Ownership", "Operations", "Inventory Search", "Azure API Dashboards"],
)

if page != "Azure API Dashboards":
    filtered_df = filtered_inventory(dm)
else:
    filtered_df = pd.DataFrame()
stats = dm.get_resource_statistics()


if page == "Azure API Dashboards":
    render_azure_api_page()

elif page == "Overview":
    st.header("Overview")
    st.markdown(
        '<div class="section-note">Portfolio snapshot from the Resources sheet, enriched with owner data where available.</div>',
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(5)
    filtered_owner_coverage = (
        (filtered_df["owner"] != UNKNOWN_OWNER).sum() / len(filtered_df)
        if len(filtered_df)
        else 0
    )
    metric_cols[0].metric("Resources", f"{len(filtered_df):,}")
    metric_cols[1].metric("Subscriptions", f"{filtered_df['subscription_id'].nunique():,}")
    metric_cols[2].metric("Resource groups", f"{filtered_df['resource_group'].nunique():,}")
    metric_cols[3].metric("Locations", f"{filtered_df['location'].nunique():,}")
    metric_cols[4].metric("Owner coverage", f"{filtered_owner_coverage:.0%}")

    st.divider()

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.subheader("Top resource types")
        type_counts = (
            filtered_df["resource_type"].value_counts().head(12).rename_axis("Resource type").reset_index(name="Count")
        )
        safe_chart(
            type_counts,
            lambda data: px.bar(data, x="Count", y="Resource type", orientation="h", text="Count"),
            "No resource type data is available for the current filters.",
        )

    with chart_cols[1]:
        st.subheader("Resources by location")
        location_counts = filtered_df["location"].replace("", "Unknown").value_counts().rename_axis("Location").reset_index(name="Count")
        safe_chart(
            location_counts,
            lambda data: px.bar(data, x="Location", y="Count", text="Count"),
            "No location data is available for the current filters.",
        )

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.subheader("Service groups")
        category_counts = filtered_df["service_category"].value_counts().rename_axis("Service group").reset_index(name="Count")
        safe_chart(
            category_counts,
            lambda data: px.bar(data, y="Service group", x="Count", orientation="h", text="Count"),
            "No service group data is available for the current filters.",
        )

    with chart_cols[1]:
        st.subheader("Workbook coverage")
        workbook_summary = dm.workbook_summary()
        st.dataframe(workbook_summary, width='stretch', hide_index=True, height=360)


elif page == "Ownership":
    st.header("Ownership")
    st.markdown(
        '<div class="section-note">Use this page to see who owns what and where ownership is missing or unclear.</div>',
        unsafe_allow_html=True,
    )

    unassigned = filtered_df[filtered_df["owner"] == UNKNOWN_OWNER]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Resources in scope", f"{len(filtered_df):,}")
    metric_cols[1].metric("Known owners", f"{filtered_df[filtered_df['owner'] != UNKNOWN_OWNER]['owner'].nunique():,}")
    metric_cols[2].metric("Unassigned", f"{len(unassigned):,}")
    metric_cols[3].metric("Coverage", f"{(1 - len(unassigned) / len(filtered_df)):.0%}" if len(filtered_df) else "0%")

    st.divider()

    owner_summary = (
        filtered_df.groupby("owner")
        .agg(
            Resources=("resource_name", "count"),
            ResourceGroups=("resource_group", "nunique"),
            Subscriptions=("subscription_id", "nunique"),
        )
        .reset_index()
        .sort_values("Resources", ascending=False)
    )

    chart_cols = st.columns([0.55, 0.45])
    with chart_cols[0]:
        st.subheader("Resources by owner")
        chart_data = owner_summary.head(15).rename(columns={"owner": "Owner"})
        safe_chart(
            chart_data,
            lambda data: px.bar(data, x="Resources", y="Owner", orientation="h", text="Resources"),
            "No ownership data is available for the current filters.",
        )
    with chart_cols[1]:
        st.subheader("Owner summary")
        st.dataframe(owner_summary, width='stretch', hide_index=True, height=420)

    st.subheader("Unassigned or unclear ownership")
    if unassigned.empty:
        st.success("All resources in the current filter have ownership data.")
    else:
        st.dataframe(
            dm.exportable_inventory(unassigned),
            width='stretch',
            hide_index=True,
            height=360,
        )


elif page == "Operations":
    st.header("Operations")
    st.markdown(
        '<div class="section-note">Operational signals are shown where the workbook provides enough detail.</div>',
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Virtual machines", f"{len(dm.sheets_data.get('Virtual Machine', [])):,}")
    metric_cols[1].metric("Storage accounts", f"{len(dm.sheets_data.get('StorageAccounts', [])):,}")
    metric_cols[2].metric("Network security groups", f"{len(dm.sheets_data.get('NSG', [])):,}")
    metric_cols[3].metric("VNet/Subnet rows", f"{len(dm.sheets_data.get('All_Vnets_Subnets_Prefix', [])):,}")

    st.divider()

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.subheader("VM status")
        vm_status = dm.vm_status_summary()
        safe_chart(
            vm_status,
            lambda data: px.bar(data, x="status", y="count", text="count", labels={"status": "Status", "count": "VMs"}),
            "No Virtual Machine sheet is available.",
        )
    with chart_cols[1]:
        st.subheader("Monitoring coverage")
        monitoring = dm.monitoring_summary()
        if monitoring.empty:
            st.info("No monitoring columns are available in the VM sheet.")
        else:
            st.dataframe(monitoring, width='stretch', hide_index=True)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.subheader("Storage security posture")
        storage_security = dm.storage_security_summary()
        if storage_security.empty:
            st.info("No StorageAccounts sheet is available.")
        else:
            long_security = storage_security.melt(id_vars="Check", value_vars=["Pass", "Fail"], var_name="Result", value_name="Accounts")
            st.plotly_chart(
                px.bar(long_security, x="Check", y="Accounts", color="Result", barmode="group", text="Accounts"),
                width='stretch',
            )
    with chart_cols[1]:
        st.subheader("Network inventory")
        network_rows = []
        for sheet in ["All_Vnets_Subnets_Prefix", "NSG", "Bastion", "Load balancers", "VPN gateways", "S2S-VPN Connections"]:
            if sheet in dm.sheets_data:
                network_rows.append({"Area": sheet, "Rows": len(dm.sheets_data[sheet])})
        if network_rows:
            st.dataframe(pd.DataFrame(network_rows), width='stretch', hide_index=True)
        else:
            st.info("No network detail sheets are available.")


else:
    st.header("Inventory Search")
    st.markdown(
        '<div class="section-note">Search and export the cleaned resource inventory. Raw Azure type values are preserved for audit and troubleshooting.</div>',
        unsafe_allow_html=True,
    )

    search_term = st.text_input("Search inventory", placeholder="Resource name, owner, type, resource group, location")
    result_df = dm.search_inventory(filtered_df, search_term)

    metric_cols = st.columns(3)
    metric_cols[0].metric("Matching resources", f"{len(result_df):,}")
    metric_cols[1].metric("Service groups", f"{result_df['service_category'].nunique():,}")
    metric_cols[2].metric("Owners", f"{result_df['owner'].nunique():,}")

    st.dataframe(
        dm.exportable_inventory(result_df),
        width='stretch',
        hide_index=True,
        height=520,
    )
    download_buttons(dm, result_df, "azure_inventory_filtered")


st.caption(
    f"Loaded {len(dm.source_sheet_names)} source workbook sheets. Primary source: Resources. "
    "Raw workbook tabs are preserved."
)
