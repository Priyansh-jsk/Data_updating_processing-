import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO, BytesIO
from autoviz import data_cleaning_suggestions, FixDQ
import openpyxl
import chardet

st.set_page_config(page_title="Data Processing App", layout="wide")

def clean_data(df):
    # st.subheader("🛠 Data Cleansing")
    #  Data Quality Issues
    st.subheader("⚠️ Data Quality Issues")
    dq_issues = data_cleaning_suggestions(df)
    st.write(dq_issues)

# this function detect file encoding
def detect_encoding(uploaded_file):
    raw_data = uploaded_file.read()
    result = chardet.detect(raw_data)
    uploaded_file.seek(0)  # Reset file pointer
    return result['encoding']

# function to load data
def load_data(uploaded_file):
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension in ['csv', 'txt']:
            encoding = detect_encoding(uploaded_file)
            # reading with detected encoding, fall back to others if needed...
            try:
                return pd.read_csv(uploaded_file, encoding=encoding)
            except:
                return pd.read_csv(uploaded_file, encoding='latin1')
        
        elif file_extension in ['xls', 'xlsx']:
            return pd.read_excel(uploaded_file)
        
        elif file_extension == 'json':
            return pd.read_json(uploaded_file)
        
        else:
            # for unstructured data, try to read as text
            try:
                content = uploaded_file.getvalue().decode('utf-8')
                return pd.DataFrame({'Raw_Content': [content]})
            except:
                st.error("Unsupported file format")
                return None
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

# function to download data
def download_data(df, format_type):
    output = BytesIO()
    
    if format_type == 'csv':
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return output
    
    elif format_type == 'excel':
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output
    
    elif format_type == 'json':
        output = StringIO()
        df.to_json(output, orient='records')
        output.seek(0)
        return output

# app main
def main():
    st.title("🥸 Fais Data Processing Application")
    st.write("Upload your dataset and perform various data processing operations..")
    
    # session state
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'original_df' not in st.session_state:
        st.session_state.original_df = None
    
    # upload dataset files
    uploaded_file = st.file_uploader(
        "Upload your dataset (CSV, Excel, JSON, TXT)", 
        type=['csv', 'xlsx', 'xls', 'json', 'txt']
    )
    
    if uploaded_file is not None:
        if st.session_state.df is None or st.button('Reload Original Data'):
            df = load_data(uploaded_file)
            if df is not None:
                st.session_state.df = df
                st.session_state.original_df = df.copy()
                st.success("Data loaded successfully!")
    
    if st.session_state.df is not None:
        df = st.session_state.df
        
        # data info display
        st.subheader("Dataset Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Rows", df.shape[0])
        col2.metric("Total Columns", df.shape[1])
        col3.metric("Missing Values", df.isna().sum().sum())
        
        # show data
        st.subheader("Data Preview")
        st.dataframe(df.head())

        df_clean = clean_data(df)
        
        # data processing options
        st.sidebar.header("Data Processing Options")
        
        # 1. Column operations
        with st.sidebar.expander("Column Operations"):
            selected_columns = st.multiselect(
                "Select columns to keep", 
                df.columns,
                default=list(df.columns)
            )
            
            if st.button("Apply Column Selection"):
                st.session_state.df = df[selected_columns]
                st.experimental_rerun()
            
            rename_col = st.selectbox("Select column to rename", df.columns)
            new_name = st.text_input("New column name")
            
            if st.button("Rename Column") and new_name:
                st.session_state.df = df.rename(columns={rename_col: new_name})
                st.experimental_rerun()
        
        # 2. Missing data handling
        with st.sidebar.expander("Missing Data Handling"):
            na_col = st.selectbox("Select column with missing values", df.columns)
            
            na_option = st.radio(
                "Choose action for missing values",
                ["Fill with value", "Fill with mean/median/mode", "Drop rows"]
            )
            
            if na_option == "Fill with value":
                fill_value = st.text_input("Value to fill")
                if st.button("Fill Missing Values"):
                    st.session_state.df[na_col] = df[na_col].fillna(fill_value)
                    st.experimental_rerun()
            
            elif na_option == "Fill with mean/median/mode":
                stat_method = st.selectbox(
                    "Select method", 
                    ["mean", "median", "mode"]
                )
                if st.button("Fill Missing Values"):
                    if stat_method == "mean":
                        fill_val = df[na_col].mean()
                    elif stat_method == "median":
                        fill_val = df[na_col].median()
                    else:  # mode
                        fill_val = df[na_col].mode()[0]
                    st.session_state.df[na_col] = df[na_col].fillna(fill_val)
                    st.experimental_rerun()
            
            elif na_option == "Drop rows":
                if st.button("Drop Rows with Missing Values"):
                    st.session_state.df = df.dropna(subset=[na_col])
                    st.experimental_rerun()
        
        # 3. Data type conversion
        with st.sidebar.expander("Data Type Conversion"):
            type_col = st.selectbox("Select column to convert", df.columns)
            new_type = st.selectbox(
                "Select new data type",
                ["string", "numeric", "datetime", "category"]
            )
            
            if st.button("Convert Data Type"):
                try:
                    if new_type == "string":
                        st.session_state.df[type_col] = df[type_col].astype(str)
                    elif new_type == "numeric":
                        st.session_state.df[type_col] = pd.to_numeric(df[type_col], errors='coerce')
                    elif new_type == "datetime":
                        st.session_state.df[type_col] = pd.to_datetime(df[type_col], errors='coerce')
                    elif new_type == "category":
                        st.session_state.df[type_col] = df[type_col].astype('category')
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Conversion error: {str(e)}")
        
        # 4. Data editing
        with st.sidebar.expander("Edit Data"):
            edit_col = st.selectbox("Select column to edit", df.columns)
            edit_row = st.number_input(
                "Row index to edit", 
                min_value=0, 
                max_value=len(df)-1, 
                value=0
            )
            new_value = st.text_input("New value")
            
            if st.button("Update Value"):
                st.session_state.df.loc[edit_row, edit_col] = new_value
                st.experimental_rerun()
        
        # 5. Filter data
        with st.sidebar.expander("Filter Data"):
            filter_col = st.selectbox("Select column to filter", df.columns)
            
            if pd.api.types.is_numeric_dtype(df[filter_col]):
                min_val = float(df[filter_col].min())
                max_val = float(df[filter_col].max())
                selected_range = st.slider(
                    "Select range",
                    min_val,
                    max_val,
                    (min_val, max_val)
                )
                if st.button("Apply Filter"):
                    st.session_state.df = df[(df[filter_col] >= selected_range[0]) & (df[filter_col] <= selected_range[1])]
                    st.experimental_rerun()
            else:
                unique_values = df[filter_col].unique()
                selected_values = st.multiselect(
                    "Select values to keep",
                    unique_values,
                    default=list(unique_values)
                )
                if st.button("Apply Filter"):
                    st.session_state.df = df[df[filter_col].isin(selected_values)]
                    st.experimental_rerun()
        
        # 6. Reset to original
        if st.sidebar.button("Reset to Original Data"):
            st.session_state.df = st.session_state.original_df.copy()
            st.experimental_rerun()
        
        # processed updated data download
        st.sidebar.header("Download Options")
        download_format = st.sidebar.selectbox(
            "Select download format",
            ["csv", "excel", "json"]
        )
        
        if st.sidebar.button("Download Processed Data"):
            processed_data = download_data(st.session_state.df, download_format)
            st.sidebar.download_button(
                label=f"Download as {download_format.upper()}",
                data=processed_data,
                file_name=f"processed_data.{download_format}",
                mime=f"application/{download_format}"
            )

if __name__ == "__main__":
    main()