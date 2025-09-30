import pandas as pd
import streamlit as st
import io

def load_data(uploaded_file):
    """Loads data from a CSV or Excel file into a pandas DataFrame."""
    if uploaded_file is None:
        return None
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_extension == 'csv':
            df = pd.read_csv(uploaded_file)
        elif file_extension in ['xls', 'xlsx']:
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload a CSV or Excel file.")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def get_data_quality_report(df):
    """Generates a comprehensive data quality report for a DataFrame."""
    if df is None:
        return "No data available."

    report_buffer = io.StringIO()
    
    report_buffer.write("### 📊 Data Quality & Cleaning Suggestions\n\n")
    report_buffer.write("Here's a quick overview of your dataset's quality:\n\n")

   
    missing_values = df.isnull().sum()
    total_missing = missing_values.sum()
    if total_missing > 0:
        report_buffer.write(f"**Missing Values:** Found **{total_missing}** missing values. \n")
        missing_per_column = missing_values[missing_values > 0]
        report_buffer.write("Columns with missing data:\n")
        for col, count in missing_per_column.items():
            percentage = (count / len(df)) * 100
            report_buffer.write(f"- **{col}:** {count} missing ({percentage:.2f}%)\n")
        report_buffer.write("*Suggestion:* Consider imputation (e.g., filling with mean/median/mode) or removing rows/columns with excessive missing data.\n\n")
    else:
        report_buffer.write("**Missing Values:** ✅ Excellent! No missing values found.\n\n")

    
    duplicate_rows = df.duplicated().sum()
    if duplicate_rows > 0:
        percentage = (duplicate_rows / len(df)) * 100
        report_buffer.write(f"**Duplicate Rows:** Found **{duplicate_rows}** duplicate rows ({percentage:.2f}% of the data).\n")
        report_buffer.write("*Suggestion:* You can remove these duplicates to prevent skewed analysis.\n\n")
    else:
        report_buffer.write("**Duplicate Rows:** ✅ Great! No duplicate rows detected.\n\n")

   
    report_buffer.write("**Data Types & Column Summary:**\n")
    for col in df.columns:
        dtype = df[col].dtype
        unique_vals = df[col].nunique()
        report_buffer.write(f"- **{col}** (`{dtype}`): {unique_vals} unique values. \n")
        
        if hasattr(df[col], 'apply'):
            mixed_types = df[col].apply(type).nunique() > 1
            if mixed_types:
                report_buffer.write("  - ⚠️ *Warning:* This column might contain mixed data types.\n")
        
        if dtype == 'object' and unique_vals > 50:
             report_buffer.write(f"  - ℹ️ *Info:* High cardinality ({unique_vals} unique values). Consider grouping or feature engineering.\n")


    report_buffer.write("\nThis initial check helps ensure your analysis starts on a solid foundation! You can ask me to perform any of these cleaning operations.")
    
    return report_buffer.getvalue()

def get_data_summary(df):
    """Creates a concise summary of the dataframe for the LLM agent."""
    if df is None:
        return ""
        
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()

    summary = f"""
    Dataset Overview:
    - Shape: {df.shape} (rows, columns)
    - Column Names and Data Types:
    {info_str}
    - First 5 rows (head):
    {df.head().to_string()}
    """
    return summary.strip()
