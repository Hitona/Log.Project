# Импорт необходимых библиотек
from datetime import datetime  # Для работы с датой и временем
from typing import Optional  # Для указания необязательных полей

from pydantic import BaseModel  # Для создания моделей данных с валидацией
from sqlalchemy import Column, Integer, String, DateTime  # Для определения столбцов таблицы в SQLAlchemy

from database import Base  # Базовый класс для моделей SQLAlchemy


# Pydantic модель для валидации данных
class LogEntryCreate(BaseModel):
    """
    Модель Pydantic для валидации данных при создании записи лога.
    Используется для проверки данных, поступающих от пользователя или из внешних источников.
    """
    timestamp: datetime  # Временная метка
    pid: int  # ID процесса
    tid: int  # ID потока
    level: str  # Уровень лога (например, "INFO", "ERROR")
    tag: Optional[str] = None  # Тег лога (необязательное поле)
    message: str  # Сообщение лога

    def to_orm(self):
        """
        Преобразует Pydantic-модель в SQLAlchemy-модель для сохранения в базе данных.
        """
        return LogEntry(
            timestamp=self.timestamp,
            pid=self.pid,
            tid=self.tid,
            level=self.level,
            tag=self.tag,
            message=self.message
        )


# SQLAlchemy модель для работы с базой данных
class LogEntry(Base):
    """
    Модель SQLAlchemy для представления таблицы `log_entries` в базе данных.
    Каждый экземпляр этого класса представляет собой запись в таблице.
    """
    __tablename__ = 'log_entries'  # Название таблицы в базе данных

    # Определение столбцов таблицы
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор записи
    timestamp = Column(DateTime, nullable=False)  # Временная метка (обязательное поле)
    pid = Column(Integer, nullable=False)  # ID процесса (обязательное поле)
    tid = Column(Integer, nullable=False)  # ID потока (обязательное поле)
    level = Column(String, nullable=False)  # Уровень лога (обязательное поле)
    tag = Column(String)  # Тег лога (необязательное поле)
    message = Column(String, nullable=False)  # Сообщение лога (обязательное поле)
