import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="PE 565 Capstone Project",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cached function to generate production data
@st.cache_data
def generate_production_data(days_count=365):
    """Generate sample petroleum production data using decline curve model."""
    days = np.arange(0, days_count, 1)
    production = 1000 * np.exp(-0.01 * days) + np.random.normal(0, 50, len(days))
    production = np.maximum(production, 0)  # Ensure non-negative values
    
    df = pd.DataFrame({
        "Day": days,
        "Production (BOE/day)": production,
        "Cumulative Production (BOE)": np.cumsum(production)
    })
    return df

# Title and header
st.title("⚙️ Petroleum Engineering Application")
st.markdown("**PE 565: Computer Programming for Petroleum Engineers - Capstone Project**")
st.markdown("---")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a section:",
    ["Home", "Analysis", "Visualization", "About"]
)

# Home page
if page == "Home":
    st.header("Welcome to PE 565 Capstone Project")
    st.write("""
    This application demonstrates the integration of:
    - **AI-Assisted Coding** for development
    - **Modern Web Frameworks** (Streamlit)
    - **Real-world Oil & Gas Data Analysis**
    
    ### Project Themes:
    - Production Analysis & Decline Curve Analysis (DCA)
    - CO₂ Storage Evaluation
    - Other petroleum engineering solutions
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Project Status", "In Development", "+1 phase")
    with col2:
        st.metric("Submission Deadline", "May 16, 2026", "15 days")
    with col3:
        st.metric("Presentation", "May 17, 2026", "5:00 PM")

# Analysis page
elif page == "Analysis":
    st.header("Data Analysis")
    
    # Sample data upload or generation
    st.subheader("Upload or Generate Data")
    
    data_source = st.radio("Select data source:", ["Upload CSV", "Generate Sample Data"])
    
    if data_source == "Generate Sample Data":
        st.write("Generating sample petroleum production data...")
        
        # Generate sample production data
        df = generate_production_data()
        
        st.write(df.head(len(df)))
        
        # Display statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Production", f"{df['Cumulative Production (BOE)'].iloc[-1]:,.0f} BOE")
        with col2:
            st.metric("Avg Daily Production", f"{df['Production (BOE/day)'].mean():.2f} BOE/day")
        with col3:
            st.metric("Peak Production", f"{df['Production (BOE/day)'].max():.2f} BOE/day")
        with col4:
            st.metric("Min Production", f"{df['Production (BOE/day)'].min():.2f} BOE/day")
    
    else:
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write(df.head(10))

# Visualization page
elif page == "Visualization":
    st.header("Data Visualization")
    
    # Generate sample data for visualization
    df = generate_production_data()
    
    # Production trend chart
    st.subheader("Production Trend")
    fig_prod = go.Figure()
    fig_prod.add_trace(go.Scatter(
        x=df["Day"],
        y=df["Production (BOE/day)"],
        fill='tozeroy',
        mode='lines',
        name='Daily Production',
        line=dict(color='#1f77b4', width=2)
    ))
    fig_prod.update_layout(
        title="Production Over Time",
        xaxis_title="Days",
        yaxis_title="Production (BOE/day)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_prod, use_container_width=True)
    
    # Cumulative production chart
    st.subheader("Cumulative Production")
    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=df["Day"],
        y=df["Cumulative Production (BOE)"],
        fill='tozeroy',
        mode='lines',
        name='Cumulative Production',
        line=dict(color='#2ca02c', width=2)
    ))
    fig_cum.update_layout(
        title="Cumulative Production Over Time",
        xaxis_title="Days",
        yaxis_title="Cumulative Production (BOE)",
        hovermode='x unified'
    )
    st.plotly_chart(fig_cum, use_container_width=True)

# About page
elif page == "About":
    st.header("About This Project")
    
    st.subheader("Project Overview")
    st.write("""
    This capstone project is developed as part of **PE 565: Computer Programming for Petroleum Engineers**.
    
    **Key Objectives:**
    - Solve a real-world upstream, midstream, or downstream engineering problem
    - Build a functional GUI using modern frameworks
    - Demonstrate effective use of AI tools for code generation and optimization
    - Handle real-world Oil & Gas datasets
    """)
    
    st.subheader("Technologies Used")
    col1, col2 = st.columns(2)
    with col1:
        st.write("""
        **Backend:**
        - Python 3.14.4
        - Pandas
        - NumPy
        - Scikit-learn
        """)
    with col2:
        st.write("""
        **Frontend:**
        - Streamlit
        - Plotly
        - Custom CSS (optional)
        """)
    
    st.subheader("Important Dates")
    st.info("""
    📅 **Submission Deadline:** May 16, 2026
    📅 **Final Presentation:** May 17, 2026 at 5:00 PM
    """)

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>"
    "PE 565 Capstone Project © 2026 | "
    "Developed with Streamlit and Python"
    "</p>",
    unsafe_allow_html=True
)
