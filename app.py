import streamlit as st
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

# Import pages
from app.pages.home import show_home_page
from app.pages.timeline import show_timeline_page
from app.pages.insights import show_insights_page

# Configure the app
st.set_page_config(
    page_title="Digital Time Capsule",
    page_icon="⏳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
def load_css():
    css_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app/static/css/style.css")
    if os.path.exists(css_file):
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS file not found. Using default styling.")

# Initialize the app
def main():
    # Load CSS
    try:
        load_css()
    except Exception as e:
        st.warning(f"CSS loading error: {str(e)}. Using default styling.")
    
    # Sidebar navigation
    st.sidebar.title("Digital Time Capsule")
    st.sidebar.subheader("AI Memory Keeper")
    
    # Navigation options
    pages = {
        "New Entry": show_home_page,
        "Timeline": show_timeline_page,
        "Insights": show_insights_page
    }
    
    selection = st.sidebar.radio("Navigate to", list(pages.keys()))
    
    # Display the selected page
    pages[selection]()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info(
        "The Digital Time Capsule helps you preserve and understand your memories "
        "through AI-powered analysis and organization."
    )

if __name__ == "__main__":
    main()
