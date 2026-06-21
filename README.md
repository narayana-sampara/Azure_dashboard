# Azure Inventory Dashboard

Manager-friendly Streamlit dashboard for reviewing live Azure resource inventory, ownership, operations signals, and searchable exports. The Excel inventory is retained as a fallback.

## What This Solution Provides

- **Overview**: resource, subscription, group, location, service group, and ownership coverage summaries with bar chart visualizations.
- **Ownership**: PIC / owner rollups plus unassigned or unclear ownership tracking.
- **Operations**: VM status, storage security posture, monitoring coverage, and network inventory counts.
- **Inventory Search**: clean searchable resource inventory with CSV and Excel export.
- **Azure API Dashboards**: live Azure inventory and cost dashboards with modern visualizations (pie charts, sunburst charts, treemaps) using Azure SDK connectivity for real-time data.
- **Workbook front tabs**: `Dashboard`, `Inventory`, `Ownership`, and `Data Dictionary` were added while preserving the original source sheets.

## Run The Dashboard

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the redesigned dashboard:

```bash
streamlit run consolidated_dashboard.py
```

The legacy command also works:

```bash
streamlit run dashboard.py
```

## Azure API Dashboard Features

The `Azure API Dashboards` page provides live Azure data visualization with diverse chart types:

### Azure Inventory Dashboard
- **Resource Types Distribution**: Interactive pie chart showing the proportional distribution of resource types
- **Service Groups Distribution**: Sunburst chart for hierarchical view of service categories
- **Resource Filtering**: Real-time filters by subscription, resource group, service group, and search

### Azure Cost Dashboard
- **Service Cost Distribution**: Sunburst chart for interactive service-level cost analysis
- **Cost by Resource Group**: Treemap visualization showing cost allocation across resource groups
- **Daily Cost Trend**: Line chart with markers tracking cost trends over time
- **Cost Filtering**: Dynamic filters by subscription, service, and resource group

### Azure Compliance Dashboard
- **Compliance Status Overview**: Metrics showing total resources, compliant count, non-compliant count, and overall compliance rate
- **Compliance Status Distribution**: Pie chart visualizing the breakdown of resources by compliance state
- **Top Policies**: Bar chart displaying the most common policy assignments affecting resources
- **Resources by Resource Group**: Stacked bar chart showing resource distribution across resource groups with compliance state breakdown
- **Resource Details View**: Interactive expandable rows for viewing detailed compliance information for each resource:
  - Resource information (ID, name, group, subscription, compliance state)
  - Policy information (assignment name, definition name, action, timestamp)
  - Inventory data (resource type, location, owner, tag count)
- **Compliance Filtering**: Dynamic filters by subscription, resource group, compliance state, and search term
- **Export Options**: Download compliance data as CSV or Excel file

## Azure API Dashboard Configuration

The `Azure API Dashboards` page can query live Azure data for:

- **Azure Inventory** from Azure Resource Graph
- **Azure Cost** from Azure Cost Management
- **Azure Compliance** from Azure Policy (via Resource Graph PolicyResources)

The page accepts these connectivity values:

- **Tenant ID**
- **Application ID / Client ID**
- **Object ID**
- **Client secret** (optional)
- **Subscription IDs** (optional allowlist)

Authentication behavior:

- If a client secret is provided, the app uses service principal authentication with Tenant ID, Application ID, and Client Secret.
- If the client secret is blank, the app uses managed identity with Application ID as the managed identity client ID.
- Object ID is displayed/recorded for operator clarity, but Azure SDK authentication uses the Application ID / Client ID.

Set non-secret Azure connection values in [azure_config.env](/Users/venkat.sampara/Projects/Azure_dashboard/azure_config.env):

```text
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<application-client-id>
AZURE_OBJECT_ID=<object-id>
AZURE_SUBSCRIPTION_IDS=<subscription-id-1>,<subscription-id-2>
```

The app loads `azure_config.env` at startup. Platform environment variables still override file values when present. The Overview, Ownership, Operations, and Inventory Search pages first load subscriptions and inventory through the direct Azure service connection. If SDK initialization, authentication, subscription discovery, or Resource Graph inventory loading fails, they fall back to `file/All_Resources_Inventory 1.xlsx` and display the Azure error.

Keep `AZURE_CLIENT_SECRET` outside the config file where possible. For local service principal testing, set it in your shell or hosting platform secret settings.

Required Azure permissions:

- **Reader** on target subscriptions for Azure Resource Graph inventory
- **Cost Management Reader**, **Billing Reader**, or equivalent for Azure Cost Management
- **Policy Insights Reader** or similar role for Azure Policy compliance data (PolicyStates in Resource Graph)

## Run With Docker

Build the container image:

```bash
docker build -t azure-inventory-dashboard .
```

Run it locally:

```bash
docker run --rm -p 8501:8501 azure-inventory-dashboard
```

Open the dashboard at:

```text
http://localhost:8501
```

The image runs Streamlit on `0.0.0.0` and honors a platform-provided `PORT` value, which makes it suitable for Azure App Service, Azure Container Apps, and similar container hosting platforms.

For hosts that require an explicit port setting, configure the app/container port as `8501` unless the platform injects a different `PORT` environment variable.

For Docker deployments, update `azure_config.env` before building the image:

```bash
docker build -t azure-inventory-dashboard .
docker run --rm -p 8501:8501 azure-inventory-dashboard
```

## Project Structure

```text
Azure_dashboard/
├── Dockerfile                     # Container image for website deployment
├── .dockerignore                  # Keeps local caches out of Docker builds
├── azure_config.env               # Azure API non-secret connection defaults
├── azure_api.py                   # Azure SDK connectivity, inventory, and cost queries
├── consolidated_dashboard.py      # Main simplified Streamlit app
├── dashboard.py                   # Legacy launcher for the main app
├── data_loader.py                 # Workbook loading, normalization, and summaries
├── file/
│   └── All_Resources_Inventory 1.xlsx
├── requirements.txt
└── README.md
```

## Workbook Notes

Azure Resource Graph is the primary inventory source. The original workbook is loaded only as a fallback and uses `Resources` as its primary inventory, enriched with ownership from `PIC` where a resource match exists. Blank `Unnamed` columns are ignored in manager-facing views.

The workbook now includes these front-facing tabs:

- `Dashboard`
- `Inventory`
- `Ownership`
- `Data Dictionary`

## Verification Baseline

For the current workbook, the normalized dashboard should show:

- 31 original source sheets
- 1,499 resources
- 5 subscriptions
- 61 resource groups
