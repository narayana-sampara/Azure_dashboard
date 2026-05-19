# Azure Inventory Dashboard

Manager-friendly Streamlit dashboard and Excel workbook for reviewing Azure resource inventory, ownership, operations signals, and searchable exports.

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

## Azure API Dashboard Configuration

The `Azure API Dashboards` page can query live Azure data for:

- **Azure Inventory** from Azure Resource Graph
- **Azure Cost** from Azure Cost Management

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

The app loads `azure_config.env` at startup. Platform environment variables still override file values when present.

Keep `AZURE_CLIENT_SECRET` outside the config file where possible. For local service principal testing, set it in your shell or hosting platform secret settings.

Required Azure permissions:

- Reader on target subscriptions for Azure Resource Graph inventory.
- Cost Management Reader, Billing Reader, or equivalent cost access for Azure Cost.

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

The original workbook tabs remain the source of truth. The dashboard uses `Resources` as the primary inventory and enriches ownership from `PIC` where a resource match exists. Blank `Unnamed` columns are ignored in manager-facing views.

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
