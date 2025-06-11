import streamlit as st
import pandas as pd
import numpy as np

def safe_numeric_conversion(series, dtype=int, default=0):
    """Safely convert series to numeric type, handling non-finite values"""
    numeric_series = pd.to_numeric(series, errors='coerce').fillna(default)
    numeric_series = numeric_series.replace([np.inf, -np.inf], default)
    return numeric_series.astype(dtype)

def find_column(df, possible_names, error_msg):
    """Find first matching column from possible names"""
    for col in possible_names:
        if col in df.columns:
            return col
    
    # Fallback: search for partial matches
    partial_matches = [col for col in df.columns 
                      if any(name.split('__')[-1].lower() in col.lower() 
                            for name in possible_names)]
    if partial_matches:
        return partial_matches[0]
    
    st.error(error_msg)
    return None

def prepare_cpm_impression_data(df):
    """Prepare impression data for CPM management"""
    if df is None or df.empty:
        st.error("No CPM data available")
        return pd.DataFrame(), pd.DataFrame()
    
    # Supply data
    supply_cols = ["supply__id", "supply__metrics_data__inventory"]
    optional_cols = ["supply__date", "supply__dimension_dict__bu", "supply__dimension_dict__property"]
    supply_cols.extend([col for col in optional_cols if col in df.columns])
    
    if "supply__metrics_data__inventory" not in df.columns:
        st.error("Inventory column not found")
        return pd.DataFrame(), pd.DataFrame()
    
    supply_data = df[supply_cols].drop_duplicates().reset_index(drop=True)
    # Initialize new_inventory as BLANK (0) - users will edit to add excess
    supply_data["new_inventory"] = 0
    supply_data["total_inventory"] = supply_data["supply__metrics_data__inventory"] + supply_data["new_inventory"]
    
    # Allocation data
    allocation_id_col = find_column(df, ['id', 'allocation_id', 'allocation__id'], "No allocation ID found")
    impressions_col = find_column(df, ['metrics_data__impressions', 'impressions', 'allocation__metrics_data__impressions'], 
                                 "No impressions column found")
    
    if not allocation_id_col or not impressions_col:
        return supply_data, pd.DataFrame()
    
    allocation_cols = [allocation_id_col, impressions_col]
    allocation_cols.extend([col for col in ["supply__date", "dimension_dict__bu", "supply__dimension_dict__property"] 
                          if col in df.columns])
    
    allocation_data = df[allocation_cols].drop_duplicates().reset_index(drop=True)
    allocation_data = allocation_data.rename(columns={
        allocation_id_col: "allocation_id", 
        impressions_col: "metrics_data__impressions"
    })
    
    # Initialize new_impressions as BLANK (0) - users will edit to add excess
    allocation_data["new_impressions"] = 0
    allocation_data["total_impressions"] = allocation_data["metrics_data__impressions"] + allocation_data["new_impressions"]
    
    return supply_data, allocation_data

def prepare_cpm_rate_data(df):
    """Prepare rate data for CPM management"""
    if df is None or df.empty:
        st.error("No CPM data available")
        return pd.DataFrame()
    
    required_cols = ["supply__id", "supply__dimension_dict__rate"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"Missing required columns: {[col for col in required_cols if col not in df.columns]}")
        return pd.DataFrame()
    
    rate_cols = required_cols.copy()
    optional_cols = ["supply__date", "supply__dimension_dict__property"]
    rate_cols.extend([col for col in optional_cols if col in df.columns])
    
    rate_data = df[rate_cols].drop_duplicates().reset_index(drop=True)
    # Initialize new_rate as BLANK (0.0) - users will edit to set new rates
    rate_data["new_rate"] = 0.0
    
    return rate_data

def prepare_cpm_data(df):
    """Main function to prepare all CPM data"""
    if df is None or df.empty:
        st.error("No CPM data available")
        return
    
    try:
        supply_data, allocation_data = prepare_cpm_impression_data(df)
        st.session_state.update({
            'cpm_supply_data': supply_data,
            'cpm_allocation_data': allocation_data,
            'cpm_rate_data': prepare_cpm_rate_data(df)
        })
    except Exception as e:
        st.error(f"Error preparing CPM data: {str(e)}")

def initialize_cpm_session_state():
    """Initialize CPM session state variables"""
    defaults = {
        "cpm_supply_data": None, "cpm_allocation_data": None, "cpm_rate_data": None,
        "show_cpm_impression_editor": False, "show_cpm_rate_editor": False, 
        "cpm_function": "Impressions"
    }
    
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

def create_data_editor(data, form_key, column_config, success_msg):
    """Generic data editor with form"""
    with st.form(form_key):
        edited_data = st.data_editor(data, use_container_width=True, column_config=column_config)
        
        # Update totals
        if "total_inventory" in edited_data.columns:
            edited_data["total_inventory"] = edited_data["supply__metrics_data__inventory"] + edited_data["new_inventory"]
        if "total_impressions" in edited_data.columns:
            edited_data["total_impressions"] = edited_data["metrics_data__impressions"] + edited_data["new_impressions"]
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Changes", type="primary"):
                return edited_data, success_msg
        with col2:
            if st.form_submit_button("🔄 Reset to Blank"):
                # Reset the editable fields to blank (0)
                if "new_inventory" in edited_data.columns:
                    edited_data["new_inventory"] = 0
                    edited_data["total_inventory"] = edited_data["supply__metrics_data__inventory"] + edited_data["new_inventory"]
                if "new_impressions" in edited_data.columns:
                    edited_data["new_impressions"] = 0
                    edited_data["total_impressions"] = edited_data["metrics_data__impressions"] + edited_data["new_impressions"]
                if "new_rate" in edited_data.columns:
                    edited_data["new_rate"] = 0.0
                return edited_data, "✅ Fields reset to blank!"
                
    return None, None

def render_cpm_impression_section():
    """Render CPM impression update section"""
    if st.session_state.cpm_function != "Impressions":
        return
        
    st.subheader("CPM Updates - Impressions")
    st.info("💡 Enter additional inventory/impressions in the 'New' columns. These will be added to existing values.")
    
    if st.button("📝 Edit CPM Impressions", key="edit_cpm_impressions_btn"):
        st.session_state.show_cpm_impression_editor = not st.session_state.show_cpm_impression_editor
    
    if not st.session_state.show_cpm_impression_editor:
        return
        
    tab1, tab2 = st.tabs(["🏭 Supply Inventory", "📊 Allocation Impressions"])
    
    with tab1:
        if st.session_state.cpm_supply_data is not None and not st.session_state.cpm_supply_data.empty:
            st.write("**Add Excess Inventory:**")
            column_config = {
                "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
                "supply__metrics_data__inventory": st.column_config.NumberColumn("Current Inventory", disabled=True),
                "new_inventory": st.column_config.NumberColumn("Additional Inventory", help="Enter excess inventory to add"),
                "total_inventory": st.column_config.NumberColumn("Total Inventory", disabled=True, help="Current + Additional")
            }
            
            result, msg = create_data_editor(st.session_state.cpm_supply_data, "supply_form", column_config, 
                                           "✅ Supply inventory changes saved!")
            if result is not None:
                st.session_state.cpm_supply_data = result
                st.success(msg)
                st.rerun()
        else:
            st.info("No supply data available")
    
    with tab2:
        if st.session_state.cpm_allocation_data is not None and not st.session_state.cpm_allocation_data.empty:
            st.write("**Add Excess Impressions:**")
            column_config = {
                "allocation_id": st.column_config.TextColumn("Allocation ID", disabled=True),
                "metrics_data__impressions": st.column_config.NumberColumn("Current Impressions", disabled=True),
                "new_impressions": st.column_config.NumberColumn("Additional Impressions", help="Enter excess impressions to add"),
                "total_impressions": st.column_config.NumberColumn("Total Impressions", disabled=True, help="Current + Additional")
            }
            
            result, msg = create_data_editor(st.session_state.cpm_allocation_data, "allocation_form", column_config,
                                           "✅ Allocation impressions changes saved!")
            if result is not None:
                st.session_state.cpm_allocation_data = result
                st.success(msg)
                st.rerun()
        else:
            st.info("No allocation data available")
    
    # Download buttons
    render_download_buttons()

def render_cpm_rate_section():
    """Render CPM rate update section"""
    if st.session_state.cpm_function != "Rate Update":
        return
        
    st.subheader("CPM Updates - Rate Update")
    st.info("💡 Enter new rates in the 'New Rate' column. Leave at 0.0 to keep original rate unchanged.")
    
    if st.button("📝 Edit CPM Rates", key="edit_cpm_rates_btn"):
        st.session_state.show_cpm_rate_editor = not st.session_state.show_cpm_rate_editor
    
    if st.session_state.show_cpm_rate_editor and st.session_state.cpm_rate_data is not None:
        column_config = {
            "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
            "supply__dimension_dict__rate": st.column_config.NumberColumn("Current Rate", disabled=True),
            "new_rate": st.column_config.NumberColumn("New Rate", help="Enter new rate (0.0 = no change)")
        }
        
        with st.form("rate_form"):
            edited_rates = st.data_editor(st.session_state.cpm_rate_data, use_container_width=True, 
                                        column_config=column_config)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    st.session_state.cpm_rate_data = edited_rates
                    st.success("✅ Rate changes saved!")
                    st.rerun()
            with col2:
                if st.form_submit_button("🔄 Reset to Blank"):
                    edited_rates["new_rate"] = 0.0
                    st.session_state.cpm_rate_data = edited_rates
                    st.success("✅ Rates reset to blank!")
                    st.rerun()
        
        # Show download for rate changes
        if st.session_state.cpm_rate_data is not None:
            rate_data = st.session_state.cpm_rate_data.copy()
            
            # Only show rates that have been changed (non-zero new_rate)
            rate_changes = rate_data[rate_data["new_rate"] > 0.0]
            
            if not rate_changes.empty:
                st.info(f"📝 {len(rate_changes)} rate(s) modified")
                download_data = rate_changes[["supply__id", "new_rate"]].copy()
                download_data.columns = ["id", "rate"]
                csv = download_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated Rates CSV", csv, "cpm_rate_update.csv", "text/csv", key="download_rates_btn")

def render_download_buttons():
    """Render download buttons for modified data"""
    # Supply inventory changes
    if st.session_state.cpm_supply_data is not None:
        supply_data = st.session_state.cpm_supply_data.copy()
        
        # Only show inventory that has been changed (non-zero new_inventory)
        supply_changes = supply_data[supply_data["new_inventory"] > 0]
        
        if not supply_changes.empty:
            st.info(f"📝 {len(supply_changes)} supply inventory record(s) modified")
            download_data = supply_changes[["supply__id", "total_inventory"]].copy()
            download_data.columns = ["id", "inventory"]
            download_data["inventory"] = safe_numeric_conversion(download_data["inventory"])
            csv = download_data.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Supply Inventory CSV", csv, "cpm_supply_inventory_update.csv", "text/csv", key="download_supply_btn")
    
    # Allocation impressions changes
    if st.session_state.cpm_allocation_data is not None:
        allocation_data = st.session_state.cpm_allocation_data.copy()
        
        # Only show impressions that have been changed (non-zero new_impressions)
        allocation_changes = allocation_data[allocation_data["new_impressions"] > 0]
        
        if not allocation_changes.empty:
            st.info(f"📝 {len(allocation_changes)} allocation impression record(s) modified")
            download_data = allocation_changes[["allocation_id", "total_impressions"]].copy()
            download_data.columns = ["id", "impressions"]
            download_data["impressions"] = safe_numeric_conversion(download_data["impressions"])
            csv = download_data.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Allocation Impressions CSV", csv, "cpm_allocation_impressions_update.csv", "text/csv", key="download_allocation_btn")

def reset_cpm_data(data_type):
    """Reset CPM data to blank values"""
    try:
        if data_type == "impressions":
            if st.session_state.cpm_supply_data is not None:
                # Reset new_inventory to blank (0)
                st.session_state.cpm_supply_data["new_inventory"] = 0
                # Reset total to original + new (which is now 0)
                st.session_state.cpm_supply_data["total_inventory"] = (
                    st.session_state.cpm_supply_data["supply__metrics_data__inventory"] + 
                    st.session_state.cpm_supply_data["new_inventory"]
                )
            if st.session_state.cpm_allocation_data is not None:
                # Reset new_impressions to blank (0)
                st.session_state.cpm_allocation_data["new_impressions"] = 0
                # Reset total to original + new (which is now 0)
                st.session_state.cpm_allocation_data["total_impressions"] = (
                    st.session_state.cpm_allocation_data["metrics_data__impressions"] + 
                    st.session_state.cpm_allocation_data["new_impressions"]
                )
        elif data_type == "rates":
            if st.session_state.cpm_rate_data is not None:
                # Reset new_rate to blank (0.0)
                st.session_state.cpm_rate_data["new_rate"] = 0.0
        
        return True
    except Exception as e:
        st.error(f"Error resetting {data_type}: {str(e)}")
        return False

def render_cpm_reset_buttons():
    """Render improved reset buttons with unique keys"""
    st.subheader("🔄 CPM Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reset Impressions", help="Reset all impression changes to blank", key="reset_impressions_btn"):
            if reset_cpm_data("impressions"):
                st.success("✅ Impressions reset to blank!")
                st.rerun()
    
    with col2:
        if st.button("🔄 Reset Rates", help="Reset all rate changes to blank", key="reset_rates_btn"):
            if reset_cpm_data("rates"):
                st.success("✅ Rates reset to blank!")
                st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All CPM", help="Clear all CPM management data", key="clear_all_cpm_btn"):
            # Clear all CPM-related session state
            cpm_keys = [key for key in st.session_state.keys() if key.startswith(('cpm_', 'show_cpm'))]
            for key in cpm_keys:
                del st.session_state[key]
            st.success("✅ All CPM data cleared!")
            st.rerun()

def render_cpm_update_section():
    """Main CPM update section"""
    st.subheader("📊 CPM Updates")
    
    # Function selector
    st.session_state.cpm_function = st.selectbox(
        "Select CPM Function:",
        ["Impressions", "Rate Update"],
        index=0 if st.session_state.get("cpm_function", "Impressions") == "Impressions" else 1,
        key="cpm_function_selector"
    )
    
    # Render appropriate section
    if st.session_state.cpm_function == "Impressions":
        render_cpm_impression_section()
    else:
        render_cpm_rate_section()