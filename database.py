import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            # Get MongoDB connection string from environment variable
            mongo_uri = os.getenv('MONGODB_URI')
            if not mongo_uri:
                logger.error("MONGODB_URI environment variable not set")
                return
            
            # Get database name from environment variable
            db_name = os.getenv('MONGODB_DB_NAME', 'course_scheduler')
            
            # Create MongoDB client
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Test the connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Get database instance
            self.db = self.client[db_name]
            logger.info(f"Using database: {db_name}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
        except ServerSelectionTimeoutError as e:
            logger.error(f"Server selection timeout: {e}")
            self.client = None
            self.db = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            self.client = None
            self.db = None
    
    def get_collection(self, collection_name):
        """Get a collection from the database"""
        if self.db is None:
            logger.error("Database connection not established")
            return None
        return self.db[collection_name]
    
    def is_connected(self):
        """Check if database is connected"""
        try:
            if self.client is None:
                return False
            # Ping the database
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def close_connection(self):
        """Close the database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def insert_document(self, collection_name, document):
        """Insert a document into a collection"""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None
            result = collection.insert_one(document)
            logger.info(f"Document inserted with ID: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            return None
    
    def find_documents(self, collection_name, query=None, limit=None):
        """Find documents in a collection"""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return []
            
            if query is None:
                query = {}
            
            cursor = collection.find(query)
            if limit:
                cursor = cursor.limit(limit)
            
            return list(cursor)
        except Exception as e:
            logger.error(f"Error finding documents: {e}")
            return []
    
    def update_document(self, collection_name, query, update_data):
        """Update a document in a collection"""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None
            
            result = collection.update_one(query, {'$set': update_data})
            logger.info(f"Documents updated: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return None
        
    def update_plan_variation(self, collection_name, plan_id, year_id, update_data):
        """Update a specific variation of a plan"""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None
            
            query = {"plan_id": plan_id, "years.id": year_id}
            update = {'$set': {f'years.$.{k}': v for k, v in update_data.items()}}
            
            result = collection.update_one(query, update)
            logger.info(f"Plan variation updated: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating plan variation: {e}")
            return None
    
    def delete_document(self, collection_name, query):
        """Delete a document from a collection"""
        try:
            collection = self.get_collection(collection_name)
            if collection is None:
                return None
            
            result = collection.delete_one(query)
            logger.info(f"Documents deleted: {result.deleted_count}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return None

# Create a global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Get the database manager instance"""
    return db_manager

def get_collection(collection_name):
    """Get a collection from the database"""
    return db_manager.get_collection(collection_name) 