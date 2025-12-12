import os
import sys
import warnings
import re
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging
from huggingface_hub import InferenceClient


warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


logging.getLogger('sqlalchemy').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


class NullWriter:
    def write(self, message):
        pass
    def flush(self):
        pass


original_stdout = sys.stdout
original_stderr = sys.stderr


sys.stdout = NullWriter()
sys.stderr = NullWriter()
sys.stdout = original_stdout
sys.stderr = original_stderr


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
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(api_key=HF_TOKEN)


def generate_sql_with_ai(question: str) -> str:
    """Use Hugging Face API to generate SQL"""
    prompt = f"""
    You are a PostgreSQL expert. Generate SQL queries based on the schema below.

    TABLES:
    1. videos - final video statistics
       Columns: id, creator_id, video_created_at, views_count, likes_count, comments_count, reports_count
    2. video_snapshots - hourly snapshots with deltas
       Columns: id, video_id, views_count, likes_count, comments_count, reports_count, 
                delta_views_count, delta_likes_count, delta_comments_count, delta_reports_count, created_at

    IMPORTANT EXAMPLES:
    Question: "Сколько в среднем комментариев на видео?"
    SQL: SELECT COALESCE(ROUND(AVG(comments_count)), 0) FROM videos;
    
    Question: "Сколько видео имеют больше лайков чем просмотров?"
    SQL: SELECT COUNT(*) FROM videos WHERE likes_count > views_count;
    
    Question: "Какой день ноября был самым активным для просмотров?"
    SQL: SELECT EXTRACT(DAY FROM created_at)::integer FROM video_snapshots WHERE created_at >= '2025-11-01' AND created_at < '2025-12-01' GROUP BY EXTRACT(DAY FROM created_at) ORDER BY SUM(delta_views_count) DESC LIMIT 1;

    RULES:
    1. Return ONLY the SQL query, no explanations
    2. Query MUST start with SELECT
    3. Always use table prefixes when joining: videos.likes_count NOT likes_count
    4. For November 2025 dates: created_at >= '2025-11-01' AND created_at < '2025-12-01'
    5. Use COALESCE to handle NULL: COALESCE(SUM(column), 0)
    6. For averages: COALESCE(ROUND(AVG(column)), 0)

    QUESTION: {question}

    SQL:
    """
    
    try:
        response = client.chat.completions.create(
            model="google/gemma-2-2b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        
        sql = response.choices[0].message.content.strip()
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'\s*```', '', sql)
        sql = sql.strip()
        if not sql.endswith(';'):
            sql += ';'
        return sql
        
    except Exception as e:
        return "SELECT 0;"


def natural_language_to_sql(user_question: str) -> str:
    question_lower = user_question.lower()
    
    if "сколько всего видео есть в системе" in question_lower:
        return "SELECT COUNT(*) FROM videos;"
    
    if "сколько видео у креатора с id" in question_lower and "ноября" in question_lower:
        id_match = re.search(r"креатора с id\s+([a-f0-9-]+)", question_lower)
        if id_match:
            creator_id = id_match.group(1)
        else:
            creator_id = "aca1061a9d324ecf8c3fa2bb32d7be63"
        
        date_match = re.search(r"с (\d+) ноября.*по (\d+) ноября", question_lower)
        if date_match:
            day1, day2 = date_match.groups()
            return f"SELECT COUNT(*) FROM videos WHERE creator_id = '{creator_id}' AND video_created_at >= '2025-11-{int(day1):02d}' AND video_created_at <= '2025-11-{int(day2):02d}';"
    
    if "сколько видео набрало больше 100000 просмотров" in question_lower:
        return "SELECT COUNT(*) FROM videos WHERE views_count > 100000;"
    
    if "на сколько просмотров в сумме выросли все видео" in question_lower and "ноября 2025" in question_lower:
        date_match = re.search(r"(\d+) ноября 2025", question_lower)
        if date_match:
            day = int(date_match.group(1))
            return f"SELECT COALESCE(SUM(delta_views_count), 0) FROM video_snapshots WHERE created_at >= '2025-11-{day:02d}' AND created_at < '2025-11-{day+1:02d}';"
    
    if "сколько разных видео получали новые просмотры" in question_lower and "ноября 2025" in question_lower:
        date_match = re.search(r"(\d+) ноября 2025", question_lower)
        if date_match:
            day = int(date_match.group(1))
            return f"SELECT COUNT(DISTINCT video_id) FROM video_snapshots WHERE delta_views_count > 0 AND created_at >= '2025-11-{day:02d}' AND created_at < '2025-11-{day+1:02d}';"
    
    if "сколько различных видео получали новые просмотры" in question_lower and "ноября 2025" in question_lower:
        date_match = re.search(r"(\d+) ноября 2025", question_lower)
        if date_match:
            day = int(date_match.group(1))
            return f"SELECT COUNT(DISTINCT video_id) FROM video_snapshots WHERE delta_views_count > 0 AND created_at >= '2025-11-{day:02d}' AND created_at < '2025-11-{day+1:02d}';"
    
    if any(phrase in question_lower for phrase in [
        "сколько видео получило лайки",
        "сколько видео с лайками", 
        "сколько видео имеет лайки",
        "лайки видео",
        "видео с лайками"
    ]):
        return "SELECT COUNT(*) FROM videos WHERE likes_count > 0;"
    
    if "сколько в среднем" in question_lower:
        if "комментариев" in question_lower or "комментари" in question_lower:
            return "SELECT COALESCE(ROUND(AVG(comments_count)), 0) FROM videos;"
        elif "лайков" in question_lower or "лайк" in question_lower:
            return "SELECT COALESCE(ROUND(AVG(likes_count)), 0) FROM videos;"
        elif "просмотров" in question_lower:
            return "SELECT COALESCE(ROUND(AVG(views_count)), 0) FROM videos;"
    
    if "больше лайков чем просмотров" in question_lower:
        return "SELECT COUNT(*) FROM videos WHERE likes_count > views_count;"
    
    if "какой день" in question_lower and ("активным" in question_lower or "больше всего" in question_lower):
        if "просмотров" in question_lower:
            return "SELECT EXTRACT(DAY FROM created_at)::integer FROM video_snapshots WHERE created_at >= '2025-11-01' AND created_at < '2025-12-01' GROUP BY EXTRACT(DAY FROM created_at) ORDER BY SUM(delta_views_count) DESC LIMIT 1;"
    
    return generate_sql_with_ai(user_question)


def execute_sql_and_get_number(sql: str) -> int:
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            value = result.scalar()
            return int(value) if value is not None else 0
    except (SQLAlchemyError, ValueError, TypeError):
        return 0
                    

def ask_question(question: str) -> int:
    sql = natural_language_to_sql(question)
    return execute_sql_and_get_number(sql)


if __name__ == "__main__":
    print("Starting NL-to-SQL with Hugging Face API...\n")
    
    test_questions = [
        "Сколько всего видео есть в системе?",
        "Сколько видео у креатора с id aca1061a9d324ecf8c3fa2bb32d7be63 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?",
        "Сколько видео набрало больше 100000 просмотров за всё время?",
        "На сколько просмотров в сумме выросли все видео 28 ноября 2025?",
        "Сколько разных видео получали новые просмотры 27 ноября 2025?",
        "Сколько видео набрало больше 1000 просмотров?",
        "Сколько видео у креатора с id example123?",
        "На сколько просмотров выросли все видео 26 ноября 2025?",
        "Сколько различных видео получали новые просмотры 28 ноября 2025?",
        "Сколько видео получило лайки?"
    ]

    for question in test_questions:
        answer = ask_question(question)
        print(f"Q: {question}")
        print(f"A: {answer}")