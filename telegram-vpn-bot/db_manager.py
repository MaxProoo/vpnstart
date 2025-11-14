import aiosqlite
import logging
import os

# Путь к базе данных (создаётся автоматически, если файла нет)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "database.db")

# Убедимся, что папка существует
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Логгер для отладки
logger = logging.getLogger(__name__)


async def init_db():
    """
    Инициализация базы данных:
    создаёт таблицы, если они не существуют.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trial_users (
                    user_id INTEGER PRIMARY KEY,
                    used_trial INTEGER DEFAULT 0,
                    sub_id TEXT,
                    expiry_date TEXT
                )
            """)
            # реф сис
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    paid BOOLEAN DEFAULT 0
                )
            """)
            await db.commit()
            logger.info("✅ База данных инициализирована успешно.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")


async def has_user_used_trial(user_id: int) -> bool:
    """
    Проверяет, использовал ли пользователь пробный период.
    Возвращает True/False.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT 1 FROM trial_users WHERE user_id = ? AND used_trial = 1",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса пробника в БД: {e}")
        return False


async def set_user_used_trial(user_id: int):
    """
    Отмечает, что пользователь использовал пробный период.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO trial_users (user_id, used_trial)
                VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET used_trial = 1
            """, (user_id,))
            await db.commit()
            logger.info(f"Пользователь {user_id} отмечен как использовавший пробник.")
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса пробника: {e}")


async def record_trial_usage(user_id: int, sub_id: str, expiry_date: str):
    """
    Записывает в базу факт использования пробного периода:
    - user_id: ID пользователя Telegram
    - sub_id: ID подписки (из Marzban)
    - expiry_date: дата окончания пробного периода
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO trial_users (user_id, used_trial, sub_id, expiry_date)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    used_trial = 1,
                    sub_id = excluded.sub_id,
                    expiry_date = excluded.expiry_date
            """, (user_id, sub_id, expiry_date))
            await db.commit()
            logger.info(f"✅ Пользователь {user_id} записан в trial_users (sub_id={sub_id}, expiry={expiry_date})")
    except Exception as e:
        logger.error(f"Ошибка при записи trial_usage для пользователя {user_id}: {e}")
