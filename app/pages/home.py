import streamlit as st
import datetime
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.firebase import add_entry
from app.models.summarizer import summarize_text, analyze_sentiment, extract_keywords

def show_home_page():
    st.title("New Memory Entry")
    st.subheader("Capture your thoughts, reflections, and experiences")
    
    # Date selection
    col1, col2 = st.columns([1, 2])
    with col1:
        entry_date = st.date_input("Date", datetime.datetime.now())
    with col2:
        entry_title = st.text_input("Title", placeholder="Give your entry a title")
    
    # Entry content
    entry_content = st.text_area(
        "Your thoughts",
        height=300,
        placeholder="Write your diary entry, reflection, or quote here...",
        help="Express yourself freely. The AI will help analyze and organize your thoughts."
    )
    
    # Mood selection
    mood_options = ["😊 Happy", "😌 Content", "😐 Neutral", "😔 Sad", "😠 Angry", "😟 Anxious", "🤔 Thoughtful", "Other"]
    selected_mood = st.selectbox("How are you feeling?", mood_options)
    
    # Tags
    tags = st.text_input(
        "Tags (optional)",
        placeholder="Add tags separated by commas (e.g., work, family, goals)",
        help="Tags help organize and find related entries later"
    )
    
    # Privacy setting
    is_private = st.checkbox("Mark as private", value=True, help="Private entries are only visible to you")
    
    # Submit button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        submit_button = st.button("Save Entry", type="primary", use_container_width=True)
    
    if submit_button and entry_content:
        with st.spinner("Processing your entry..."):
            # Process the entry with NLP
            summary = summarize_text(entry_content, max_length=100, min_length=20)
            sentiment = analyze_sentiment(entry_content)
            keywords = extract_keywords(entry_content)
            
            # Prepare entry data
            entry_data = {
                "title": entry_title,
                "content": entry_content,
                "date": entry_date.isoformat(),
                "timestamp": datetime.datetime.now(),
                "mood": selected_mood,
                "tags": [tag.strip() for tag in tags.split(",")] if tags else [],
                "is_private": is_private,
                "summary": summary,
                "sentiment": sentiment,
                "keywords": keywords
            }
            
            # Save to Firebase
            try:
                entry_id = add_entry(entry_data)
                if entry_id:
                    st.success("Entry saved successfully!")
                    
                    # Show summary and analysis
                    st.subheader("AI Analysis")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Summary:**")
                        st.write(summary)
                    
                    with col2:
                        st.markdown("**Emotional Tone:**")
                        st.write(f"{sentiment['emotion'].title()} ({sentiment['score']:.2f})")
                        
                        st.markdown("**Keywords:**")
                        st.write(", ".join(keywords))
                    
                    # Clear the form
                    st.button("Write Another Entry")
                else:
                    st.error("Failed to save entry. Please try again.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    elif submit_button:
        st.warning("Please write something before saving.")
    
    # Tips section
    with st.expander("Tips for meaningful entries"):
        st.markdown("""
        - **Be specific** about what happened and how you felt
        - **Reflect** on why certain events or feelings were significant
        - **Connect** current experiences with past ones
        - **Ask questions** that prompt deeper thinking
        - **Express gratitude** for positive aspects of your day
        """)
