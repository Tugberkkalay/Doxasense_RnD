# app/db/mongo_session.py
import os
from pymongo import MongoClient
from datetime import datetime
import uuid

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = "doxasense_mind"

# Global client
_client = None
_db = None

def get_mongo_client():
    """Get MongoDB client (singleton)"""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URL)
    return _client

def get_mongo_db():
    """Get MongoDB database"""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[DATABASE_NAME]
    return _db

def get_db():
    """FastAPI dependency for MongoDB"""
    return get_mongo_db()

# Helper functions for document operations
class DocumentDB:
    def __init__(self, db):
        self.db = db
        self.documents = db.documents
        self.normalized_docs = db.normalized_docs
    
    def create_document(self, data: dict) -> dict:
        """Create a document"""
        doc = {
            "_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow(),
            **data
        }
        self.documents.insert_one(doc)
        return doc
    
    def get_document(self, doc_id: str) -> dict:
        """Get document by ID"""
        return self.documents.find_one({"_id": doc_id})
    
    def update_document(self, doc_id: str, data: dict):
        """Update document"""
        self.documents.update_one({"_id": doc_id}, {"$set": data})
    
    def list_documents(self, skip: int = 0, limit: int = 50, status: str = None):
        """List documents with pagination"""
        query = {}
        if status:
            query["status"] = status
        
        cursor = self.documents.find(query).sort("created_at", -1).skip(skip).limit(limit)
        return list(cursor), self.documents.count_documents(query)
    
    def create_normalized_doc(self, data: dict) -> dict:
        """Create normalized document"""
        doc = {
            "_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow(),
            **data
        }
        self.normalized_docs.insert_one(doc)
        return doc
    
    def get_normalized_docs_by_document(self, document_id: str):
        """Get all normalized docs for a document"""
        return list(self.normalized_docs.find({"document_id": document_id}))
