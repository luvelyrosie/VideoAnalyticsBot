import json
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


load_dotenv()


def get_database_url():
    """Get database URL - handles ${VARIABLE} expansion"""
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        if "${" in db_url:
            import re
            variables = re.findall(r'\$\{([^}]+)\}', db_url)
            for var in variables:
                value = os.getenv(var, "")
                db_url = db_url.replace(f"${{{var}}}", value)
        return db_url
    
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_NAME = os.getenv("POSTGRES_DB", "video_stats")
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres123")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    
    return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def load_data():
    JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "videos.json")
    
    print(f"Loading data from: {JSON_PATH}")
    print(f"Database URL: {DATABASE_URL}")
    
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, list):
        videos_data = raw_data
    elif isinstance(raw_data, dict) and "videos" in raw_data:
        videos_data = raw_data["videos"]
    else:
        raise ValueError("JSON format not recognized. Expected array or object with 'videos' key.")

    session = SessionLocal()
    try:
        print(f"Found {len(videos_data)} videos. Starting insert...")

        for video in videos_data:
            video_insert = text("""
                INSERT INTO videos (
                    id, creator_id, video_created_at,
                    views_count, likes_count, comments_count, reports_count,
                    created_at, updated_at
                ) VALUES (
                    :id, :creator_id, :video_created_at,
                    :views_count, :likes_count, :comments_count, :reports_count,
                    NOW(), NOW()
                ) ON CONFLICT (id) DO NOTHING
            """)

            session.execute(video_insert, {
                "id": video["id"],
                "creator_id": str(video["creator_id"]),
                "video_created_at": video["video_created_at"],
                "views_count": video.get("views_count", 0),
                "likes_count": video.get("likes_count", 0),
                "comments_count": video.get("comments_count", 0),
                "reports_count": video.get("reports_count", 0),
            })

            if "snapshots" in video and video["snapshots"]:
                snapshot_insert = text("""
                    INSERT INTO video_snapshots (
                        id, video_id, created_at,
                        views_count, likes_count, comments_count, reports_count,
                        delta_views_count, delta_likes_count,
                        delta_comments_count, delta_reports_count,
                        updated_at
                    ) VALUES (
                        :id, :video_id, :created_at,
                        :views_count, :likes_count, :comments_count, :reports_count,
                        :delta_views_count, :delta_likes_count,
                        :delta_comments_count, :delta_reports_count,
                        NOW()
                    ) ON CONFLICT (id) DO NOTHING
                """)

                for snap in video["snapshots"]:
                    session.execute(snapshot_insert, {
                        "id": snap["id"],
                        "video_id": video["id"],
                        "created_at": snap["created_at"],
                        "views_count": snap.get("views_count", 0),
                        "likes_count": snap.get("likes_count", 0),
                        "comments_count": snap.get("comments_count", 0),
                        "reports_count": snap.get("reports_count", 0),
                        "delta_views_count": snap.get("delta_views_count", 0),
                        "delta_likes_count": snap.get("delta_likes_count", 0),
                        "delta_comments_count": snap.get("delta_comments_count", 0),
                        "delta_reports_count": snap.get("delta_reports_count", 0),
                    })

        session.commit()
        print(f"Successfully loaded {len(videos_data)} videos!")

    except Exception as e:
        session.rollback()
        print(f"Error during loading: {e}")
        raise
    finally:
        session.close()
        
        
if __name__ == "__main__":
    load_data()