# Импорт необходимых библиотек
import base64  # Для работы с base64 (кодирование/декодирование)
import io  # Для работы с потоками ввода-вывода
import os  # Для работы с файловой системой
import re  # Для работы с регулярными выражениями
import shutil  # Для работы с файлами и директориями (копирование, удаление и т.д.)
from datetime import datetime  # Для работы с датой и временем
from typing import Dict, List, Optional  # Для аннотации типов

import matplotlib.pyplot as plt  # Для построения графиков
from fastapi import FastAPI, UploadFile, File, Request, HTTPException, Depends  # FastAPI для создания веб-приложения
from fastapi.responses import HTMLResponse, RedirectResponse  # Для работы с HTTP-ответами
from fastapi.staticfiles import StaticFiles  # Для работы со статическими файлами
from fastapi.templating import Jinja2Templates  # Для работы с шаблонами HTML
from sqlalchemy.orm import Session  # Для работы с базой данных через SQLAlchemy

from database import get_db, init_db  # Функции для работы с базой данных
from models import LogEntry  # Модель данных для логов

# Инициализация базы данных
init_db()

# Создание экземпляра FastAPI
app = FastAPI()

# Подключаем статические файлы (CSS, JS, изображения и т.д.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Инициализация шаблонов Jinja2 для HTML-страниц
templates = Jinja2Templates(directory="templates")

# Глобальная переменная для хранения загруженных данных
uploaded_data: Optional[Dict] = None


# Функция для парсинга времени в логах
def parse_datetime(timestamp: str) -> datetime:
    """
    Преобразует строку времени в формате "MM-DD HH:MM:SS.fff" в объект datetime.
    """
    return datetime.strptime(timestamp, "%m-%d %H:%M:%S.%f")


# Функция для парсинга лог-файла logcat
def parse_logcat(file_path: str) -> List[Dict]:
    """
    Парсит файл логов logcat и возвращает список словарей с данными логов.
    """
    logs = []
    # Регулярное выражение для разбора строк логов
    log_pattern = re.compile(
        r'(?P<timestamp>\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+'  # Время
        r'(?P<pid>\d+)\s+'  # ID процесса
        r'(?P<tid>\d+)\s+'  # ID потока
        r'(?P<level>[VDIWEAF])\s+'  # Уровень лога (V, D, I, W, E, A, F)
        r'(?P<tag>\S+)\s*:\s+'  # Тег лога
        r'(?P<message>.*)'  # Сообщение лога
    )
    # Открываем файл и читаем его построчно
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = log_pattern.match(line.strip())  # Применяем регулярное выражение
            if match:
                log_data = match.groupdict()  # Преобразуем результат в словарь
                log_data['timestamp'] = parse_datetime(log_data['timestamp'])  # Парсим время
                logs.append(log_data)  # Добавляем лог в список
    return logs


# Функция для фильтрации логов по уровню и поисковому запросу
def analyze_logs(logs: List[Dict], level: Optional[str] = None, search: Optional[str] = None) -> List[Dict]:
    """
    Фильтрует логи по уровню (level) и поисковому запросу (search).
    """
    filtered_logs = logs

    # Фильтрация по уровню лога
    if level:
        filtered_logs = [log for log in filtered_logs if log['level'].upper() == level.upper()]

    # Фильтрация по поисковому запросу
    if search:
        filtered_logs = [log for log in filtered_logs if search.lower() in log['message'].lower()]

    return filtered_logs


# Функция для создания столбчатого графика количества логов по уровням
def create_level_histogram(logs: List[Dict]) -> str:
    """
    Создает столбчатый график количества логов по уровням и возвращает его в формате base64.
    """
    # Извлекаем уровни логов
    levels = [log['level'] for log in logs]
    # Считаем количество логов для каждого уровня
    level_counts = {level: levels.count(level) for level in set(levels)}

    # Создаем график
    plt.figure(figsize=(10, 6))
    bars = plt.bar(list(level_counts.keys()), list(level_counts.values()), color='blue')
    plt.xlabel('Уровень', fontsize=14)
    plt.ylabel('Количество логов', fontsize=14)
    plt.title('Количество логов по уровням', fontsize=16)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid(True)

    # Добавляем значения на вершины столбцов
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval + 0.05, str(int(yval)), ha='center', va='bottom')

    # Сохранение графика в формате base64
    buf = io.BytesIO()  # Создаем буфер в памяти
    plt.savefig(buf, format='png')  # Сохраняем график в буфер
    plt.close()  # Закрываем график
    buf.seek(0)  # Перемещаем указатель буфера в начало
    img_str = base64.b64encode(buf.read()).decode('utf-8')  # Кодируем график в base64
    return img_str


# Главная страница
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """
    Возвращает главную страницу приложения.
    """
    return templates.TemplateResponse("index.html", {"request": request})


# Загрузка файла и его обработка
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Обрабатывает загруженный файл, парсит его и сохраняет данные в базу данных.
    """
    global uploaded_data
    upload_dir = "uploads"  # Директория для загрузки файлов
    os.makedirs(upload_dir, exist_ok=True)  # Создаем директорию, если она не существует

    # Сохраняем загруженный файл
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)  # Копируем содержимое файла в буфер

    try:
        logs = parse_logcat(file_path)  # Парсим файл логов
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при парсинге файла: {e}")

    # Сохраняем данные в глобальную переменную
    uploaded_data = {
        "logs": logs,
        "original_format": "logcat"
    }

    # Сохраняем логи в базу данных
    for log_entry in logs:
        db_log = LogEntry(**log_entry)  # Создаем объект модели LogEntry
        db.add(db_log)  # Добавляем объект в сессию
    db.commit()  # Сохраняем изменения в базе данных

    # Перенаправляем пользователя на страницу с таблицей
    return RedirectResponse(url="/tables", status_code=303)


# Страница с таблицей данных и фильтрацией
@app.get("/tables", response_class=HTMLResponse)
async def get_tables(request: Request, level: Optional[str] = None, search: Optional[str] = None):
    """
    Возвращает страницу с таблицей логов, отфильтрованных по уровню и поисковому запросу.
    """
    global uploaded_data
    if not uploaded_data:
        return RedirectResponse(url="/", status_code=303)  # Если данные не загружены, перенаправляем на главную

    # Фильтруем логи
    data = analyze_logs(uploaded_data["logs"], level, search)

    # Возвращаем HTML-страницу с данными
    return templates.TemplateResponse("tables.html", {
        "request": request,
        "data": data,
        "level": level,
        "search": search
    })


# Страница с графиками
@app.get("/graphs", response_class=HTMLResponse)
async def get_graphs(request: Request):
    """
    Возвращает страницу с графиками, основанными на загруженных логах.
    """
    global uploaded_data
    if not uploaded_data:
        return RedirectResponse(url="/", status_code=303)  # Если данные не загружены, перенаправляем на главную

    # Создаем гистограмму уровней логов
    level_histogram = create_level_histogram(uploaded_data["logs"])

    # Возвращаем HTML-страницу с графиком
    return templates.TemplateResponse("graphs.html", {
        "request": request,
        "level_histogram": level_histogram
    })


# Страница с данными (без кнопок скачивания)
@app.get("/data", response_class=HTMLResponse)
async def get_data(request: Request):
    """
    Возвращает страницу с данными.
    """
    return templates.TemplateResponse("data.html", {"request": request})


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    # Запуск сервера Uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
