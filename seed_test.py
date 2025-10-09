from app import app, mongo

with app.app_context():
    try:
        db = mongo.db
        # List collections to verify connection
        collections = db.list_collection_names()
        print("✅ MongoDB connected successfully!")
        print("Existing collections:", collections)
    except Exception as e:
        print("❌ MongoDB connection failed:", str(e))
