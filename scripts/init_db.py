from app.database import Base, engine
import app.models
Base.metadata.create_all(engine)
print("Database schema created. No fake or synthetic records were inserted.")
