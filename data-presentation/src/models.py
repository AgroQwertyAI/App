from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class TimeRange(BaseModel):
    """Определение временного диапазона для запросов."""
    start: datetime
    end: datetime
    format: Optional[str] = None


class TableRequest(BaseModel):
    """Запрос на создание таблицы из данных сообщений."""
    time: TimeRange
    columns: List[str]
    format: str = "xlsx"


class ChartDefinition(BaseModel):
    """Определение параметров диаграммы."""
    chart_type: str
    label_field: str  # Имя поля для метки (ось X или сектор)
    value_aggregation: str  # Тип агрегации: count/sum
    value_field: Optional[str] = None  # Имя поля для значения (используется при value_aggregation='sum')
    series_field: Optional[str] = None  # Имя поля для серии (используется только для stacked_bar)
    title: str


class ChartRequest(BaseModel):
    """Запрос на создание диаграммы из данных сообщений."""
    time: TimeRange
    chart_definition: ChartDefinition


class ChartDataset(BaseModel):
    """Набор данных для диаграммы (одна серия)."""
    label: str
    data: List[float]


class ChartResponse(BaseModel):
    """Ответ с данными для диаграммы."""
    chartType: str
    title: str
    labels: List[str]
    datasets: List[ChartDataset]


def apply_mapping(message: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    """Applies mapping to a message and returns a dictionary with redefined keys."""
    result = {}

    for source_path, target_key in mapping.items():
        if source_path == 'data' and isinstance(target_key, dict):
            for data_source, data_target in target_key.items():
                if isinstance(message.get('data'), dict):
                    result[data_target] = message['data'].get(data_source)
                else:
                    result[data_target] = None
        else:
            result[target_key] = message.get(source_path, None)

    return result
