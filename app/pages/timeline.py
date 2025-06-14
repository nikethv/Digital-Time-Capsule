import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.firebase import get_entries, delete_entry

def show_timeline_page():
    st.title("Memory Timeline")
    st.subheader("Explore your journey through time")
    
    # Filters
    with st.expander("Filters", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range filter
            date_range = st.date_input(
                "Date range",
                value=(
                    datetime.datetime.now() - datetime.timedelta(days=30),
                    datetime.datetime.now()
                ),
                help="Filter entries by date range"
            )
            
            # Tags filter
            tags_filter = st.text_input(
                "Filter by tags",
                placeholder="Enter tags separated by commas",
                help="Show only entries with specific tags"
            )
        
        with col2:
            # Mood filter
            mood_options = ["All", "😊 Happy", "😌 Content", "😐 Neutral", "😔 Sad", "😠 Angry", "😟 Anxious", "🤔 Thoughtful", "Other"]
            selected_mood = st.selectbox("Filter by mood", mood_options)
            
            # Sentiment filter
            sentiment_options = ["All", "Very Positive", "Positive", "Neutral", "Negative", "Very Negative"]
            selected_sentiment = st.selectbox("Filter by emotional tone", sentiment_options)
    
    # Get entries from Firebase
    with st.spinner("Loading your memories..."):
        entries = get_entries(limit=100)
        
        if not entries:
            st.info("No entries found. Start by adding a new entry on the 'New Entry' page.")
            return
        
        # Apply filters
        filtered_entries = []
        for entry in entries:
            # Convert string date to datetime for comparison
            try:
                entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()
            except (ValueError, TypeError):
                # If date parsing fails, use timestamp
                entry_date = entry.get('timestamp', datetime.datetime.now()).date()
            
            # Apply date filter
            if len(date_range) == 2:
                if not (date_range[0] <= entry_date <= date_range[1]):
                    continue
            
            # Apply mood filter
            if selected_mood != "All" and entry.get('mood', '') != selected_mood:
                continue
            
            # Apply sentiment filter
            if selected_sentiment != "All" and entry.get('sentiment', {}).get('emotion', '').lower() != selected_sentiment.lower():
                continue
            
            # Apply tags filter
            if tags_filter:
                filter_tags = [tag.strip().lower() for tag in tags_filter.split(',')]
                entry_tags = [tag.lower() for tag in entry.get('tags', [])]
                if not any(tag in entry_tags for tag in filter_tags):
                    continue
            
            filtered_entries.append(entry)
    
    # Display emotional trend chart
    if filtered_entries:
        st.subheader("Emotional Trends")
        
        # Prepare data for the chart
        chart_data = []
        for entry in filtered_entries:
            try:
                entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()
            except (ValueError, TypeError):
                entry_date = entry.get('timestamp', datetime.datetime.now()).date()
            
            sentiment_score = entry.get('sentiment', {}).get('score', 0.5)
            sentiment_category = entry.get('sentiment', {}).get('emotion', 'neutral')
            
            chart_data.append({
                'date': entry_date,
                'sentiment_score': sentiment_score,
                'sentiment_category': sentiment_category.title(),
                'title': entry.get('title', 'Untitled')
            })
        
        # Create DataFrame
        df = pd.DataFrame(chart_data)
        
        # Sort by date
        df = df.sort_values('date')
        
        # Create line chart
        fig = px.line(
            df, 
            x='date', 
            y='sentiment_score',
            color_discrete_sequence=['#1f77b4'],
            labels={'sentiment_score': 'Emotional Positivity', 'date': 'Date'},
            hover_data=['title', 'sentiment_category']
        )
        
        # Add markers for individual entries
        fig.add_scatter(
            x=df['date'], 
            y=df['sentiment_score'],
            mode='markers',
            marker=dict(
                size=10,
                color=df['sentiment_score'],
                colorscale='RdYlGn',
                showscale=False
            ),
            hovertemplate='<b>%{customdata[0]}</b><br>Date: %{x}<br>Emotion: %{customdata[1]}<extra></extra>',
            customdata=df[['title', 'sentiment_category']],
            showlegend=False
        )
        
        # Customize layout
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_title="",
            yaxis_title="",
            yaxis=dict(
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                ticktext=['Very Negative', 'Negative', 'Neutral', 'Positive', 'Very Positive']
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Display entries in timeline format
    st.subheader("Your Memories")
    
    if not filtered_entries:
        st.info("No entries match your filters. Try adjusting your filter criteria.")
    else:
        # Group entries by month
        entries_by_month = {}
        for entry in filtered_entries:
            try:
                entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()
            except (ValueError, TypeError):
                entry_date = entry.get('timestamp', datetime.datetime.now()).date()
            
            month_key = entry_date.strftime("%B %Y")
            if month_key not in entries_by_month:
                entries_by_month[month_key] = []
            
            entries_by_month[month_key].append(entry)
        
        # Sort months in reverse chronological order
        sorted_months = sorted(
            entries_by_month.keys(),
            key=lambda x: datetime.datetime.strptime(x, "%B %Y"),
            reverse=True
        )
        
        # Display entries by month
        for month in sorted_months:
            with st.expander(month, expanded=(month == sorted_months[0])):
                for entry in sorted(
                    entries_by_month[month],
                    key=lambda x: datetime.datetime.fromisoformat(x.get('date', '')).date() if isinstance(x.get('date', ''), str) else x.get('timestamp', datetime.datetime.now()).date(),
                    reverse=True
                ):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        # Entry card
                        sentiment = entry.get('sentiment', {}).get('emotion', 'neutral')
                        sentiment_color = {
                            'very positive': '#28a745',
                            'positive': '#5cb85c',
                            'neutral': '#6c757d',
                            'negative': '#dc3545',
                            'very negative': '#dc3545'
                        }.get(sentiment.lower(), '#6c757d')
                        
                        st.markdown(f"""
                        <div style="border-left: 5px solid {sentiment_color}; padding-left: 10px; margin-bottom: 20px;">
                            <h4>{entry.get('title', 'Untitled')}</h4>
                            <p style="color: #6c757d; font-size: 0.8em;">
                                {entry.get('date', '')} • {entry.get('mood', 'No mood')} • 
                                <span style="color: {sentiment_color};">{sentiment.title()}</span>
                            </p>
                            <p>{entry.get('summary', entry.get('content', '')[:100] + '...')}</p>
                            <p style="font-size: 0.8em;">
                                {', '.join([f'<span style="background-color: #f8f9fa; padding: 2px 5px; border-radius: 3px; margin-right: 5px;">{tag}</span>' for tag in entry.get('tags', [])])}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        # View full entry button
                        if st.button("View", key=f"view_{entry.get('id', '')}", help="View full entry"):
                            st.session_state['selected_entry'] = entry
                        
                        # Delete entry button
                        if st.button("Delete", key=f"delete_{entry.get('id', '')}", help="Delete this entry"):
                            if delete_entry(entry.get('id')):
                                st.success("Entry deleted successfully!")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to delete entry.")
    
    # Display full entry if selected
    if 'selected_entry' in st.session_state:
        entry = st.session_state['selected_entry']
        
        with st.sidebar:
            st.subheader(entry.get('title', 'Untitled'))
            st.write(f"Date: {entry.get('date', '')}")
            st.write(f"Mood: {entry.get('mood', 'Not specified')}")
            
            st.markdown("**Content:**")
            st.write(entry.get('content', ''))
            
            st.markdown("**AI Analysis:**")
            st.write(f"Emotional tone: {entry.get('sentiment', {}).get('emotion', 'neutral').title()}")
            st.write(f"Summary: {entry.get('summary', 'No summary available')}")
            
            if entry.get('keywords'):
                st.write(f"Keywords: {', '.join(entry.get('keywords', []))}")
            
            if st.button("Close", key="close_entry"):
                del st.session_state['selected_entry']
                st.experimental_rerun()
