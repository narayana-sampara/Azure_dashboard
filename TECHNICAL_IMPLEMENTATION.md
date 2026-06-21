# Compliance Dashboard - Technical Implementation Details

## Architecture

The compliance dashboard is built on a 3-tier architecture:

### 1. Data Access Layer (azure_api.py)

**New Method: `query_compliance()`**

```python
def query_compliance(self, subscription_ids: Iterable[str]) -> pd.DataFrame:
    """Query Azure Policy compliance state for resources using Azure Resource Graph."""
```

**Query Strategy:**
- Uses Azure Resource Graph PolicyResources table
- Filters for `microsoft.policyinsights/policystates` resources
- Extracts compliance state, policy assignments, and resource details
- Returns normalized pandas DataFrame

**Key Fields Extracted:**
- `resource_id`: Full Resource Manager ID
- `resource_name`: Display name
- `resource_group`: Container resource group
- `subscription_id`: Azure subscription ID
- `compliance_state`: Compliant/NonCompliant/Unknown
- `policy_assignment_name`: Policy being evaluated
- `policy_definition_name`: Policy definition
- `policy_definition_action`: Action type (Audit/Deny/etc)
- `timestamp`: Last evaluation time

**Error Handling:**
- The main dashboard loads inventory directly from Azure Resource Graph
- Azure subscription and inventory failures fall back to `file/All_Resources_Inventory 1.xlsx`
- The active source and Azure failure reason are displayed in the dashboard
- Manual refresh clears cached Azure data and retries the direct service connection

### 2. Data Integration Layer (azure_api.py)

**Updated Method: `load_inventory_and_costs()`**

Added compliance data to return dictionary:
```python
return {
    "subscriptions": subscriptions,
    "inventory": inventory,
    "costs": costs,
    "compliance": compliance,  # NEW
}
```

This ensures compliance data flows through the same pipeline as inventory and cost data.

### 3. Presentation Layer (consolidated_dashboard.py)

**New Function: `render_azure_compliance_dashboard()`**

Parameters:
- `subscriptions`: DataFrame of Azure subscriptions
- `compliance`: DataFrame of compliance data
- `inventory`: DataFrame of resources (for enrichment)

**Sections:**

1. **Data Validation**
   - Checks for empty compliance data
   - Provides helpful message if no data available

2. **Data Enrichment**
   - Maps subscription IDs to names
   - Creates inventory lookup for resource details
   - Merges compliance with inventory data

3. **Filtering System**
   - 4 interactive filters (subscription, resource group, compliance state, search)
   - Real-time filtering with user interaction

4. **Metrics Section**
   - Calculates key performance indicators
   - Total resources, compliant, non-compliant, unknown counts
   - Compliance rate percentage
   - Displays in 5-column metric layout

5. **Visualization Section**
   - Compliance status pie chart (using Plotly Express)
   - Top policies bar chart
   - Resource group distribution stacked bar chart
   - Uses `safe_chart()` wrapper for error handling

6. **Data Table**
   - Displays filtered resources with relevant columns
   - Streamlit dataframe widget with sorting/filtering capabilities
   - Height set to 420px for visibility

7. **Interactive Details View**
   - Dropdown selector for resource selection
   - Expandable accordions (st.expander) for each resource
   - Shows resource info, policy info, inventory data
   - Includes formatted key-value pairs

8. **Export Function**
   - Leverages existing `dataframe_download_buttons()`
   - CSV and Excel export options
   - Downloads compliance data for external analysis

## Data Flow

```
Azure Subscriptions
       ↓
Azure Resource Graph (PolicyResources table)
       ↓
query_compliance() method
       ↓
Compliance DataFrame
       ↓
load_inventory_and_costs()
       ↓
Azure Data Dictionary
       ↓
render_azure_compliance_dashboard()
       ↓
Streamlit UI with filtering & visualization
```

## Integration Points

### With Azure Inventory Tab
- Shares same subscription list
- Can cross-reference resource details
- Resource IDs match for correlation

### With Streamlit Caching
- Uses existing `@st.cache_data` pattern
- 30-minute TTL for compliance data
- Reduces Azure API calls

### With UI Components
- Reuses `safe_chart()` error handling
- Consistent with existing filter patterns
- Uses same color schemes and styling

## Performance Considerations

**Query Optimization:**
- Single Resource Graph query for all subscriptions
- Filters at query level for compliance state
- Orders results for faster rendering

**Data Processing:**
- DataFrame operations for filtering
- Memory efficient with filtered views
- Lazy evaluation of visualizations

**Caching:**
- 30-minute cache on Azure data refresh
- Session state tracking to avoid duplicate queries
- Selective clearing on manual refresh

## Error Handling

**Graceful Degradation:**
- Missing compliance data: shows info message, no errors
- Invalid filters: returns empty results
- Network issues: relies on Azure SDK exception handling

**User Feedback:**
- Info messages for empty datasets
- Warnings for access issues
- Error messages for configuration problems

## Extensibility

**Future Enhancements:**
1. Add remediation workflow UI
2. Integrate with Azure Automation
3. Add custom policy definitions
4. Implement compliance trend charts
5. Add policy recommendation engine

## Testing Checklist

- [ ] Dashboard loads with Azure credentials
- [ ] Compliance data appears in table
- [ ] Pie chart renders correctly
- [ ] Policy bar chart shows top policies
- [ ] Resource group chart displays properly
- [ ] All filters work independently and together
- [ ] Resource details expand correctly
- [ ] CSV export works
- [ ] Excel export works
- [ ] Search functionality works
- [ ] No data scenario handled gracefully

## Dependencies

**Required:**
- pandas >= 2.0.0
- streamlit >= 1.28.0
- plotly >= 5.0.0
- azure-mgmt-resourcegraph >= 8.0.0

**Note:** Already included in requirements.txt

## Security Considerations

- Credentials handled by Azure SDK (not in dashboard code)
- Policy Insights Reader role scoped to subscriptions
- No credentials stored in dashboard code
- Config file protected by .gitignore
- Sensitive data (timestamps, IDs) displayed safely

## Future Improvements

### Short Term
- Add compliance trend tracking (compliance over time)
- Implement resource remediation recommendations
- Add policy compliance rules details

### Medium Term
- Integration with Azure Defender for resource security findings
- Automated remediation workflow
- Email alerts for compliance violations

### Long Term
- Machine learning for compliance predictions
- Automated policy recommendations
- Industry-specific compliance dashboards (PCI, HIPAA, etc)
