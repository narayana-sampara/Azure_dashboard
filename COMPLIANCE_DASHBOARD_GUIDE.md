# Azure Compliance Dashboard Guide

## Overview

The new **Azure Compliance Dashboard** provides a comprehensive view of Azure Policy compliance status across your subscriptions. It enables you to:

- View compliance and non-compliance status of resources in your Azure subscriptions
- Analyze which policies resources are compliant or non-compliant with
- Drill down into individual resources to understand compliance details
- Export compliance data for reporting and auditing purposes

## Accessing the Compliance Dashboard

1. Open the dashboard: `streamlit run consolidated_dashboard.py`
2. Navigate to **Azure API Dashboards** from the sidebar
3. Configure your Azure credentials (Tenant ID, Application ID, Client Secret/Managed Identity)
4. Click **Refresh Azure API data**
5. Select the **Azure Compliance** tab

## Features

### Overview Metrics

At the top of the dashboard, you'll see key compliance metrics:

- **Total Resources**: Number of resources being evaluated
- **Compliant**: Count of resources meeting all policy requirements
- **Non-Compliant**: Count of resources that violate one or more policies
- **Unknown**: Resources where compliance status couldn't be determined
- **Compliance Rate**: Percentage of compliant resources (Compliant / Total Resources)

### Filtering

Use the filter bar to narrow down resources:

- **Subscription**: Filter by specific Azure subscription
- **Resource group**: Filter by resource group name
- **Compliance state**: Filter by compliance status (All, Compliant, Non-Compliant, Unknown)
- **Search**: Full-text search across all fields

### Visualizations

1. **Compliance Status Distribution** (Pie Chart)
   - Shows the proportion of resources in each compliance state
   - Hover over slices for exact counts

2. **Top Policies** (Bar Chart)
   - Lists the most frequently assigned policies
   - Helps identify which policies impact the most resources

3. **Resources by Resource Group and Compliance State** (Stacked Bar Chart)
   - Shows resource distribution across resource groups
   - Breakdown by compliance state within each group
   - Useful for identifying problem areas

### Resource Details View

#### Table View

The **Resource Details** table displays all resources matching your filters with:

- **Resource**: Resource name
- **Resource Group**: Azure resource group
- **Subscription**: Azure subscription
- **Compliance State**: Current compliance status
- **Policy Assignment**: Name of the policy assignment
- **Policy Definition**: Name of the policy definition

#### Expandable Details

To view comprehensive details about a specific resource:

1. Select a resource from the **"Select a resource to view details"** dropdown
2. Click the expand arrow (chevron) to view detailed information

Each expanded view shows:

**Resource Information**
- Resource ID (full Azure Resource Manager ID)
- Resource Name
- Resource Group
- Subscription
- Current Compliance State

**Policy Information**
- Policy Assignment name
- Policy Definition name
- Policy Action (Audit, Deny, etc.)
- Last Evaluated timestamp

**Inventory Data** (if available)
- Resource Type
- Location
- Owner/PIC tag
- Number of tags applied

### Data Export

Download compliance data in multiple formats:

- **Download CSV**: Export filtered data as comma-separated values
- **Download Excel**: Export filtered data as an Excel workbook

Exported files include all columns from the Resource Details table for external analysis and reporting.

## Understanding Compliance States

### Compliant
The resource meets the requirements of the policy. No action needed.

### Non-Compliant
The resource violates the policy requirements. Review the resource configuration and either:
- Remediate the resource to meet the policy requirement
- Exclude the resource from the policy if applicable
- Review and update the policy if the requirement is no longer valid

### Unknown
The compliance state could not be determined. This might occur if:
- The resource doesn't apply to the policy
- Policy evaluation is still in progress
- There's a configuration issue with the policy

## Common Use Cases

### 1. Compliance Audit
Filter by "Non-Compliant" to identify all resources that need remediation:
1. Set Compliance state filter to "Non-Compliant"
2. Review the Top Policies chart to understand which policies are most violated
3. Export the list for audit documentation

### 2. Resource Group Analysis
Use the "Resources by Resource Group" chart to identify which resource groups have the most compliance issues:
1. Look for resource groups with high non-compliant counts
2. Click into that group using the Resource Group filter
3. Review resources and coordinate remediation

### 3. Policy Impact Assessment
Review the "Top Policies" chart to understand which policies are most frequently triggered:
1. Identify the top policies affecting your environment
2. Click on a policy to review resources affected by it
3. Determine if the policy requirement needs adjustment or resource remediation

### 4. Owner/PIC Communication
Export compliance data and group by owner to communicate with resource owners:
1. Filter to Non-Compliant resources
2. Export as Excel
3. Use Resource Details to identify owners
4. Share list with owners for remediation action items

## Prerequisites

### Azure Permissions

Your Azure service principal or managed identity needs these permissions on target subscriptions:

- **Reader** - Required to access resource properties
- **Policy Insights Reader** - Required to read Azure Policy compliance state

### Azure Policy Setup

Ensure Azure Policy is configured in your subscriptions:

1. At least one policy is assigned to your subscriptions
2. Policy compliance evaluation is enabled
3. Policies are evaluating resources (may take time after initial setup)

## Troubleshooting

### "No Azure Policy compliance data was returned"

**Possible causes:**
- Azure Policy is not configured in your subscriptions
- The identity doesn't have "Policy Insights Reader" permission
- Compliance evaluation hasn't completed yet (allow 24+ hours after policy assignment)

**Solution:**
1. Verify Azure Policy assignments exist in your subscriptions
2. Check that your identity has appropriate permissions
3. Wait for compliance evaluation to complete
4. Try refreshing the data again

### "Expected results not showing"

**Possible causes:**
- Filters are too restrictive
- Azure Region policy scope limitations
- Resource doesn't match policy scope

**Solution:**
1. Clear/adjust filters starting with "All" selections
2. Try different subscription or resource group selections
3. Check policy scope settings in Azure Portal

### Performance is slow

**Possible causes:**
- Large number of resources and policy assignments
- Network connectivity issues
- Initial compliance evaluation in progress

**Solution:**
1. Use filters to reduce data volume
2. Try again later if compliance evaluation is in progress
3. Check network connectivity

## Integration with Other Dashboards

The **Azure Compliance** tab works alongside other dashboards:

- **Azure Inventory**: Compare resource list with compliance status
- **Azure Cost**: Correlate costs with compliance status (non-compliant resources may have higher operational costs)

Switch between tabs using the tab navigation at the top of the page.

## Tips & Best Practices

1. **Regular Monitoring**: Check the compliance dashboard weekly to track trends
2. **Export for Records**: Export compliance data monthly for compliance documentation
3. **Action Items**: Use the Resource Details view to create remediation tickets
4. **Dashboard Sharing**: Share filtered views with team members by sharing the URL
5. **Remediation Tracking**: Use filtering to track progress on remediation efforts

## Technical Details

### Data Source

Compliance data is sourced from **Azure Policy via Azure Resource Graph**:

- Query: PolicyResources table with PolicyStates
- Refresh: Data refreshes on demand when you click "Refresh Azure API data"
- Cache: Results are cached for 30 minutes to improve performance

### Data Fields

The compliance dashboard includes these fields for each resource:

- `resource_id`: Full Azure Resource Manager ID
- `resource_name`: Display name of the resource
- `resource_group`: Resource group containing the resource
- `subscription_id`: Subscription ID
- `subscription_name`: Subscription display name
- `compliance_state`: Current compliance status
- `policy_assignment_id`: ID of the policy assignment
- `policy_assignment_name`: Name of the policy assignment
- `policy_definition_id`: ID of the policy definition
- `policy_definition_name`: Name of the policy definition
- `policy_definition_action`: Action type (Audit, Deny, etc.)
- `timestamp`: Last evaluation timestamp

## Support & Feedback

For issues or questions about the compliance dashboard:

1. Check the troubleshooting section above
2. Review Azure Policy documentation
3. Verify Azure permissions and policy configuration
