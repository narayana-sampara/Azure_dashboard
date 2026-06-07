# Compliance Dashboard - Quick Start

## What's New?

A complete **Azure Compliance Dashboard** has been added to your Azure Inventory Dashboard. This new feature allows you to view and manage Azure Policy compliance across your subscriptions.

## Files Modified

1. **azure_api.py**
   - Added `query_compliance()` method to fetch compliance data from Azure Policy
   - Updated `load_inventory_and_costs()` to include compliance data

2. **consolidated_dashboard.py**
   - Added "Azure Compliance" tab to Azure API Dashboards
   - Added `render_azure_compliance_dashboard()` function with full compliance visualization

3. **README.md**
   - Added Azure Compliance Dashboard feature documentation
   - Updated required permissions

## Quick Start

### 1. Update Azure Credentials (if needed)

Edit `azure_config.env`:
```
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-app-id>
AZURE_OBJECT_ID=<your-object-id>
AZURE_SUBSCRIPTION_IDS=<subscription-ids>
```

### 2. Set Required Azure Permissions

Ensure your Azure service principal has:
- **Reader** role on target subscriptions
- **Policy Insights Reader** role for compliance data access

### 3. Ensure Azure Policy is Configured

Make sure at least one policy is assigned in your subscriptions. Compliance evaluation must be enabled.

### 4. Run the Dashboard

```bash
streamlit run consolidated_dashboard.py
```

### 5. Access the Compliance Dashboard

1. Select "Azure API Dashboards" from the sidebar
2. Enter Azure credentials and click "Refresh Azure API data"
3. Click the **"Azure Compliance"** tab

## Key Features

✅ **Compliance Overview Metrics**
- Total resources, compliant count, non-compliant count, compliance rate

✅ **Visualizations**
- Compliance status pie chart
- Top policies bar chart
- Resource distribution by resource group

✅ **Resource Filtering**
- By subscription, resource group, compliance state, and search term

✅ **Detailed Resource View**
- Click to expand any resource
- View resource info, policy info, and inventory data
- See compliance state, policy assignment, and last evaluated time

✅ **Data Export**
- Download as CSV or Excel for reporting

## Features in Detail

### Compliance Metrics
- Shows total resources, compliant/non-compliant counts
- Displays overall compliance percentage
- Updates based on selected filters

### Visualizations
1. **Compliance Distribution Pie Chart** - See proportions of compliant vs non-compliant
2. **Top Policies Bar Chart** - Identify most frequently assigned policies
3. **Resource Group Distribution Chart** - Track compliance by organizational unit

### Filtering System
- **Subscription Filter** - Select single or all subscriptions
- **Resource Group Filter** - Drill down to specific resource groups
- **Compliance State Filter** - View only compliant, non-compliant, or unknown resources
- **Search Filter** - Full-text search across all resource data

### Resource Details
Click on a resource in the dropdown to see:
- **Resource Information**: ID, name, group, subscription, state
- **Policy Information**: Assignment, definition, action, timestamp
- **Inventory Data**: Type, location, owner, tags

### Export Options
- **CSV Export** - For spreadsheet analysis
- **Excel Export** - For professional reporting

## Troubleshooting

### No compliance data showing?
1. Ensure Azure Policy is assigned in your subscriptions
2. Check that your identity has Policy Insights Reader permission
3. Wait 24+ hours after policy assignment for initial evaluation
4. Try clicking "Refresh Azure API data" again

### Can't see specific resources?
1. Check the compliance state filter - may need to set to "All"
2. Try removing the resource group filter
3. Use search to find specific resources

### Need help?
See [COMPLIANCE_DASHBOARD_GUIDE.md](./COMPLIANCE_DASHBOARD_GUIDE.md) for detailed documentation.

## Next Steps

1. Review resources in the dashboard
2. Identify non-compliant resources needing remediation
3. Export data for compliance reporting
4. Share dashboards with team members for monitoring

Enjoy your new compliance visibility! 🎉
