import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from datetime import datetime
import sys

# Add path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Firebase configuration from the provided config
FIREBASE_CONFIG = {
  "apiKey": "AIzaSyC***********************wdoPz4DQ",
  "authDomain": "digital-time-capsule-****.firebaseapp.com",
  "projectId": "digital-time-capsule-****",
  "storageBucket": "digital-time-capsule-****.firebasestorage.app",
  "messagingSenderId": "8407********",
  "appId": "1:8407********:web:********************",
  "measurementId": "G-**********"
}


class FirebaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Firebase connection"""
        self.app = None
        self.db = None
        self.is_available = False
        
        try:
            # Check if app is already initialized
            self.app = firebase_admin.get_app()
        except ValueError:
            # Initialize with service account if available
            try:
                if os.path.exists('firebase-key.json'):
                    cred = credentials.Certificate('firebase-key.json')
                    self.app = firebase_admin.initialize_app(cred)
                else:
                    # For development purposes, we'll use the config directly
                    # In production, use a service account key file
                    self.app = firebase_admin.initialize_app()
            except Exception as e:
                print(f"Error initializing Firebase: {e}")
                return
        
        try:
            self.db = firestore.client()
            self.is_available = True
            print("Firebase initialized successfully")
        except Exception as e:
            print(f"Firebase Firestore not available: {e}")
            print("The application will run in demo mode with local storage.")
            self.is_available = False
    
    def add_entry(self, entry_data):
        """Add a new diary entry to Firestore"""
        if not self.is_available:
            # Demo mode: store in memory or local file
            return self._add_entry_local(entry_data)
            
        if not self.db:
            print("Firebase not initialized")
            return None
            
        # Add timestamp if not provided
        if 'timestamp' not in entry_data:
            entry_data['timestamp'] = datetime.now()
            
        try:
            # Add entry to the 'entries' collection
            entry_ref = self.db.collection('entries').document()
            entry_ref.set(entry_data)
            return entry_ref.id
        except Exception as e:
            print(f"Error adding entry to Firestore: {e}")
            # Fallback to local storage
            return self._add_entry_local(entry_data)
    
    def _add_entry_local(self, entry_data):
        """Store entry locally when Firestore is not available"""
        # Generate a simple ID
        import uuid
        entry_id = str(uuid.uuid4())
        
        # Add ID to the data
        entry_data['id'] = entry_id
        
        # Store in memory (this will be lost when the app restarts)
        if not hasattr(self, 'local_entries'):
            self.local_entries = []
        
        self.local_entries.append(entry_data)
        
        # Optionally save to a local JSON file
        try:
            local_file = 'local_entries.json'
            if os.path.exists(local_file):
                with open(local_file, 'r') as f:
                    entries = json.load(f)
            else:
                entries = []
            
            entries.append(entry_data)
            
            with open(local_file, 'w') as f:
                # Convert datetime objects to strings
                json.dump(entries, f, default=str, indent=2)
        except Exception as e:
            print(f"Error saving to local file: {e}")
        
        return entry_id
    
    def get_entries(self, limit=50, order_by='timestamp', descending=True):
        """Get diary entries from Firestore"""
        if not self.is_available:
            # Demo mode: return from memory or local file
            return self._get_entries_local(limit, order_by, descending)
            
        if not self.db:
            print("Firebase not initialized")
            return []
        
        try:    
            # Query entries collection
            query = self.db.collection('entries')
            
            # Apply ordering
            if order_by:
                direction = firestore.Query.DESCENDING if descending else firestore.Query.ASCENDING
                query = query.order_by(order_by, direction=direction)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
                
            # Execute query
            entries = []
            for doc in query.stream():
                entry = doc.to_dict()
                entry['id'] = doc.id
                entries.append(entry)
                
            return entries
        except Exception as e:
            print(f"Error getting entries from Firestore: {e}")
            # Fallback to local storage
            return self._get_entries_local(limit, order_by, descending)
    
    def _get_entries_local(self, limit=50, order_by='timestamp', descending=True):
        """Get entries from local storage when Firestore is not available"""
        entries = []
        
        # First check memory
        if hasattr(self, 'local_entries'):
            entries = self.local_entries
        
        # Then check local file
        if not entries:
            try:
                local_file = 'local_entries.json'
                if os.path.exists(local_file):
                    with open(local_file, 'r') as f:
                        entries = json.load(f)
            except Exception as e:
                print(f"Error reading from local file: {e}")
        
        # Sort entries
        if order_by and entries:
            entries.sort(key=lambda x: x.get(order_by, ''), reverse=descending)
        
        # Apply limit
        if limit and len(entries) > limit:
            entries = entries[:limit]
            
        return entries
    
    def get_entry(self, entry_id):
        """Get a specific entry by ID"""
        if not self.is_available:
            # Demo mode: get from memory or local file
            return self._get_entry_local(entry_id)
            
        if not self.db:
            print("Firebase not initialized")
            return None
        
        try:
            doc = self.db.collection('entries').document(entry_id).get()
            if doc.exists:
                entry = doc.to_dict()
                entry['id'] = doc.id
                return entry
            return None
        except Exception as e:
            print(f"Error getting entry from Firestore: {e}")
            # Fallback to local storage
            return self._get_entry_local(entry_id)
    
    def _get_entry_local(self, entry_id):
        """Get a specific entry from local storage"""
        # Check memory
        if hasattr(self, 'local_entries'):
            for entry in self.local_entries:
                if entry.get('id') == entry_id:
                    return entry
        
        # Check local file
        try:
            local_file = 'local_entries.json'
            if os.path.exists(local_file):
                with open(local_file, 'r') as f:
                    entries = json.load(f)
                
                for entry in entries:
                    if entry.get('id') == entry_id:
                        return entry
        except Exception as e:
            print(f"Error reading from local file: {e}")
        
        return None
    
    def update_entry(self, entry_id, data):
        """Update an existing entry"""
        if not self.is_available:
            # Demo mode: update in memory or local file
            return self._update_entry_local(entry_id, data)
            
        if not self.db:
            print("Firebase not initialized")
            return False
        
        try:
            self.db.collection('entries').document(entry_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating entry in Firestore: {e}")
            # Fallback to local storage
            return self._update_entry_local(entry_id, data)
    
    def _update_entry_local(self, entry_id, data):
        """Update an entry in local storage"""
        # Update in memory
        if hasattr(self, 'local_entries'):
            for i, entry in enumerate(self.local_entries):
                if entry.get('id') == entry_id:
                    self.local_entries[i].update(data)
                    break
        
        # Update in local file
        try:
            local_file = 'local_entries.json'
            if os.path.exists(local_file):
                with open(local_file, 'r') as f:
                    entries = json.load(f)
                
                for i, entry in enumerate(entries):
                    if entry.get('id') == entry_id:
                        entries[i].update(data)
                        break
                
                with open(local_file, 'w') as f:
                    json.dump(entries, f, default=str, indent=2)
                    
                return True
        except Exception as e:
            print(f"Error updating entry in local file: {e}")
        
        return False
    
    def delete_entry(self, entry_id):
        """Delete an entry"""
        if not self.is_available:
            # Demo mode: delete from memory or local file
            return self._delete_entry_local(entry_id)
            
        if not self.db:
            print("Firebase not initialized")
            return False
        
        try:
            self.db.collection('entries').document(entry_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting entry from Firestore: {e}")
            # Fallback to local storage
            return self._delete_entry_local(entry_id)
    
    def _delete_entry_local(self, entry_id):
        """Delete an entry from local storage"""
        # Delete from memory
        if hasattr(self, 'local_entries'):
            self.local_entries = [entry for entry in self.local_entries if entry.get('id') != entry_id]
        
        # Delete from local file
        try:
            local_file = 'local_entries.json'
            if os.path.exists(local_file):
                with open(local_file, 'r') as f:
                    entries = json.load(f)
                
                entries = [entry for entry in entries if entry.get('id') != entry_id]
                
                with open(local_file, 'w') as f:
                    json.dump(entries, f, default=str, indent=2)
                    
                return True
        except Exception as e:
            print(f"Error deleting entry from local file: {e}")
        
        return False

# Create a singleton instance
firebase = FirebaseManager()

# Helper functions for easy access
def add_entry(entry_data):
    return firebase.add_entry(entry_data)

def get_entries(limit=50, order_by='timestamp', descending=True):
    return firebase.get_entries(limit, order_by, descending)

def get_entry(entry_id):
    return firebase.get_entry(entry_id)

def update_entry(entry_id, data):
    return firebase.update_entry(entry_id, data)

def delete_entry(entry_id):
    return firebase.delete_entry(entry_id)
