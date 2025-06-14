import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import random
import sys
import os
from collections import Counter
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.firebase import get_entries
from app.models.summarizer import extract_keywords

def show_insights_page():
    st.title("Memory Insights")
    st.subheader("AI-powered analysis of your memories")
    
    # Get entries from Firebase
    with st.spinner("Analyzing your memories..."):
        entries = get_entries(limit=200)
        
        if not entries:
            st.info("No entries found. Start by adding a new entry on the 'New Entry' page.")
            return
    
    # Time period selector
    time_periods = {
        "Last 7 days": 7,
        "Last 30 days": 30,
        "Last 90 days": 90,
        "Last 6 months": 180,
        "Last year": 365,
        "All time": 9999
    }
    
    selected_period = st.selectbox("Time period", list(time_periods.keys()))
    days_to_include = time_periods[selected_period]
    
    # Filter entries by time period
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_include)
    filtered_entries = []
    
    for entry in entries:
        try:
            entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()
            entry_datetime = datetime.datetime.combine(entry_date, datetime.time())
        except (ValueError, TypeError):
            entry_datetime = entry.get('timestamp', datetime.datetime.now())
        
        if entry_datetime >= cutoff_date:
            filtered_entries.append(entry)
    
    # Display metrics
    if filtered_entries:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entries", len(filtered_entries))
        
        with col2:
            # Calculate average sentiment
            sentiment_scores = [entry.get('sentiment', {}).get('score', 0.5) for entry in filtered_entries]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Map to emotional category
            if avg_sentiment >= 0.8:
                emotion = "Very Positive"
            elif avg_sentiment >= 0.6:
                emotion = "Positive"
            elif avg_sentiment >= 0.4:
                emotion = "Neutral"
            elif avg_sentiment >= 0.2:
                emotion = "Negative"
            else:
                emotion = "Very Negative"
                
            st.metric("Average Mood", emotion)
        
        with col3:
            # Count unique tags
            all_tags = []
            for entry in filtered_entries:
                all_tags.extend(entry.get('tags', []))
            
            unique_tags = len(set(all_tags))
            st.metric("Unique Topics", unique_tags)
        
        with col4:
            # Calculate writing streak
            dates = []
            for entry in filtered_entries:
                try:
                    entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()
                except (ValueError, TypeError):
                    entry_date = entry.get('timestamp', datetime.datetime.now()).date()
                
                dates.append(entry_date)
            
            # Count consecutive days
            if dates:
                dates.sort(reverse=True)
                streak = 1
                for i in range(1, len(dates)):
                    if (dates[i-1] - dates[i]).days == 1:
                        streak += 1
                    else:
                        break
                
                st.metric("Current Streak", f"{streak} days")
            else:
                st.metric("Current Streak", "0 days")
    
    # Emotional distribution chart
    if filtered_entries:
        st.subheader("Emotional Distribution")
        
        # Count sentiment categories
        sentiment_counts = Counter()
        for entry in filtered_entries:
            sentiment = entry.get('sentiment', {}).get('emotion', 'neutral')
            sentiment_counts[sentiment.title()] += 1
        
        # Prepare data for pie chart
        labels = list(sentiment_counts.keys())
        values = list(sentiment_counts.values())
        
        # Color mapping
        colors = {
            'Very Positive': '#28a745',
            'Positive': '#5cb85c',
            'Neutral': '#6c757d',
            'Negative': '#dc3545',
            'Very Negative': '#c82333'
        }
        
        color_values = [colors.get(label, '#6c757d') for label in labels]
        
        # Create pie chart
        fig = px.pie(
            values=values,
            names=labels,
            color=labels,
            color_discrete_map={label: color for label, color in zip(labels, color_values)},
            hole=0.4
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Cluster analysis
    if filtered_entries and len(filtered_entries) >= 3:
        st.subheader("Entry Clusters")
        
        n_clusters = min(5, len(filtered_entries))
        
        # Define a local cluster_entries function since import is failing
        def cluster_entries(entries, n_clusters=5):
            if len(entries) < n_clusters:
                return [0] * len(entries)  # Not enough entries to cluster
            
            try:
                # Extract text content from entries
                texts = [entry.get('content', '') for entry in entries]
                
                # Create TF-IDF vectors
                vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
                X = vectorizer.fit_transform(texts)
                
                # Apply KMeans clustering
                kmeans = KMeans(n_clusters=min(n_clusters, len(entries)), random_state=42)
                clusters = kmeans.fit_predict(X)
                
                return clusters.tolist()
            except Exception as e:
                st.error(f"Error clustering entries: {e}")
                return [0] * len(entries)  # Default cluster
        
        clusters = cluster_entries(filtered_entries, n_clusters=n_clusters)
        
        # Group entries by cluster
        entries_by_cluster = {}
        for entry, cluster_id in zip(filtered_entries, clusters):
            if cluster_id not in entries_by_cluster:
                entries_by_cluster[cluster_id] = []
            entries_by_cluster[cluster_id].append(entry)
        
        # Generate cluster names based on common keywords
        cluster_names = {}
        for cluster_id, cluster_entries in entries_by_cluster.items():
            # Collect all keywords
            all_keywords = []
            for entry in cluster_entries:
                all_keywords.extend(entry.get('keywords', []))
            
            # Count keyword frequencies
            keyword_counts = Counter(all_keywords)
            
            # Get most common keywords
            common_keywords = [kw for kw, _ in keyword_counts.most_common(2)]
            
            if common_keywords:
                cluster_names[cluster_id] = " & ".join(common_keywords).title()
            else:
                # Fallback to a generic name
                cluster_names[cluster_id] = f"Cluster {cluster_id + 1}"
        
        # Display clusters
        for cluster_id, name in cluster_names.items():
            with st.expander(f"{name} ({len(entries_by_cluster[cluster_id])} entries)"):
                for entry in entries_by_cluster[cluster_id][:5]:  # Show only top 5 entries per cluster
                    st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <h5>{entry.get('title', 'Untitled')}</h5>
                        <p style="color: #6c757d; font-size: 0.8em;">{entry.get('date', '')}</p>
                        <p>{entry.get('summary', entry.get('content', '')[:100] + '...')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if len(entries_by_cluster[cluster_id]) > 5:
                    st.write(f"... and {len(entries_by_cluster[cluster_id]) - 5} more entries")
    
    # Common themes visualization (replaced wordcloud with bar chart)
    st.subheader("Common Themes & Topics")
    
    # Extract all tags and keywords
    all_tags = []
    all_keywords = []
    
    for entry in filtered_entries:
        all_tags.extend(entry.get('tags', []))
        all_keywords.extend(entry.get('keywords', []))
    
    # Combine tags and keywords
    all_terms = all_tags + all_keywords
    term_counts = Counter(all_terms)
    
    # Display top terms
    if term_counts:
        # Create a horizontal bar chart
        top_terms = dict(term_counts.most_common(10))
        
        fig = px.bar(
            x=list(top_terms.values()),
            y=list(top_terms.keys()),
            orientation='h',
            labels={'x': 'Frequency', 'y': 'Term'},
            color=list(top_terms.values()),
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis=dict(autorange="reversed")
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add more entries with tags and keywords to see common themes.")
    
    # Monthly writing activity
    if filtered_entries:
        st.subheader("Writing Activity")
        
        # Count entries by month
        entries_by_month = {}
        for entry in filtered_entries:
            try:
                entry_date = datetime.datetime.fromisoformat(entry.get('date', '')).date()
            except (ValueError, TypeError):
                entry_date = entry.get('timestamp', datetime.datetime.now()).date()
            
            month_key = entry_date.strftime("%Y-%m")
            if month_key not in entries_by_month:
                entries_by_month[month_key] = 0
            
            entries_by_month[month_key] += 1
        
        # Sort months chronologically
        sorted_months = sorted(entries_by_month.keys())
        
        # Prepare data for the chart
        months_formatted = [datetime.datetime.strptime(month, "%Y-%m").strftime("%b %Y") for month in sorted_months]
        counts = [entries_by_month[month] for month in sorted_months]
        
        # Create bar chart
        fig = px.bar(
            x=months_formatted,
            y=counts,
            labels={'x': 'Month', 'y': 'Number of Entries'},
            color=counts,
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # AI-generated insights
    if filtered_entries:
        st.subheader("AI Insights")
        
        # Generate some example insights based on the data
        insights = []
        
        # Mood trends
        sentiment_scores = [entry.get('sentiment', {}).get('score', 0.5) for entry in filtered_entries]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        if avg_sentiment > 0.7:
            insights.append("Your entries show a consistently positive emotional tone. Keep up the good vibes!")
        elif avg_sentiment < 0.3:
            insights.append("Your recent entries show a more negative emotional tone. Consider reflecting on what might be affecting your mood.")
        
        # Writing frequency
        if len(filtered_entries) > 10 and selected_period in ["Last 30 days", "Last 90 days"]:
            insights.append(f"You've written {len(filtered_entries)} entries in this period. Regular reflection is great for emotional well-being!")
        
        # Most common emotions
        if sentiment_counts:
            most_common_emotion = sentiment_counts.most_common(1)[0][0]
            insights.append(f"Your most frequent emotional tone is '{most_common_emotion}'. This suggests a consistent pattern in how you process experiences.")
        
        # Common themes
        if term_counts:
            top_term = term_counts.most_common(1)[0][0]
            insights.append(f"'{top_term}' appears frequently in your entries. This seems to be an important theme in your life right now.")
        
        # Display insights
        if insights:
            for i, insight in enumerate(insights):
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="margin: 0;"><strong>Insight {i+1}:</strong> {insight}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Add more entries to receive AI-generated insights about your writing patterns.")
