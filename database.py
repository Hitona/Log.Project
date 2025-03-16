# Импорт необходимых компонентов из SQLAlchemy
from sqlalchemy import create_engine  # Для создания движка базы данных
from sqlalchemy.ext.declarative import declarative_base  # Для создания базового класса моделей
from sqlalchemy.orm import sessionmaker  # Для создания сессий базы данных

# URL для подключения к базе данных SQLite
# SQLite — это встроенная база данных, которая хранится в файле (в данном случае logs.db)
SQLALCHEMY_DATABASE_URL = "sqlite:///./logs.db"

# Создание движка базы данных
# `create_engine` создает соединение с базой данных
# Параметр `connect_args={"check_same_thread": False}` позволяет использовать одно соединение в нескольких потоках
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Создание фабрики сессий
# `SessionLocal` — это класс, который будет создавать сессии для взаимодействия с базой данных
# Параметры:
# - `autocommit=False`: Отключает автоматическое подтверждение изменений (нужно явно вызывать commit)
# - `autoflush=False`: Отключает автоматическую синхронизацию изменений с базой данных
# - `bind=engine`: Указывает, какой движок базы данных использовать
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание базового класса для моделей
# Все модели (таблицы) будут наследоваться от этого класса
Base = declarative_base()


# Функция для получения сессии базы данных
def get_db():
    """
    Генератор, который возвращает сессию базы данных.
    После завершения работы с сессией она автоматически закрывается.
    """
    db = SessionLocal()  # Создаем новую сессию
    try:
        yield db  # Возвращаем сессию для использования
    finally:
        db.close()  # Закрываем сессию после завершения работы


# Функция для инициализации базы данных
def init_db():
    """
    Создает все таблицы в базе данных на основе моделей, которые наследуются от `Base`.
    """
    from models import Base  # Импортируем базовый класс моделей

    # Создаем все таблицы в базе данных
    # `Base.metadata.create_all` проверяет, какие таблицы еще не созданы, и создает их
    Base.metadata.create_all(bind=engine)