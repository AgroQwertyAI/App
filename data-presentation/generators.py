import io
import logging
from typing import List, Dict, Any, Protocol
from enum import Enum
from collections import Counter

import pandas as pd
from fastapi.responses import StreamingResponse, JSONResponse, Response


# Base types
class TableFormat(str, Enum):
    xlsx = "xlsx"
    csv = "csv"
    json = "json"


# Logger setup
logger = logging.getLogger(__name__)


def create_dataframe(messages: List[Dict[str, Any]]) -> pd.DataFrame:
    """Converts a list of messages into a DataFrame."""
    if not messages:
        return pd.DataFrame()

    # First collect all unique keys from data
    all_data_keys = set()
    for msg in messages:
        if isinstance(msg.get('data'), dict):
            all_data_keys.update(msg['data'].keys())

    # Create records for DataFrame
    records = []
    for msg in messages:
        record = {
            'sender': msg.get('sender'),
            'text': msg.get('text'),
            'type': msg.get('type'),
        }

        if isinstance(msg.get('data'), dict):
            for key in all_data_keys:
                record[f'data_{key}'] = msg['data'].get(key)
        else:
            for key in all_data_keys:
                record[f'data_{key}'] = None

        records.append(record)

    return pd.DataFrame(records)


class TableGenerator(Protocol):
    def __call__(self, df: pd.DataFrame, filename: str) -> Response: ...


def xlsx_generator(df: pd.DataFrame, filename: str) -> StreamingResponse:
    """Generates XLSX file from DataFrame."""
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def csv_generator(df: pd.DataFrame, filename: str) -> StreamingResponse:
    """Generates CSV file from DataFrame."""
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    content = output.getvalue().encode('utf-8')
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def json_generator(df: pd.DataFrame, _: str) -> JSONResponse:
    """Generates JSON representation of DataFrame."""
    # Replace NaN values with None for proper JSON serialization
    content = df.replace({pd.NA: None, float('nan'): None}).to_dict(orient='records')
    return JSONResponse(content=content)


# Dictionary of table generators
TABLE_GENERATORS: Dict[TableFormat, TableGenerator] = {
    TableFormat.xlsx: xlsx_generator,
    TableFormat.csv: csv_generator,
    TableFormat.json: json_generator,
}


def generate_table_response(df: pd.DataFrame, format: TableFormat, filename_base: str) -> Response:
    """Dispatcher for creating tables in the specified format."""
    filename = f"{filename_base}.{format.value}"

    generator = TABLE_GENERATORS.get(format)
    if not generator:
        raise ValueError(f"Unsupported table format: {format}")

    try:
        return generator(df, filename)
    except Exception as e:
        logger.error(f"Error creating {format.value}: {str(e)}")
        raise


class ChartGenerator(Protocol):
    def __call__(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]: ...


def sender_activity_chart(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Creates data for sender activity chart."""
    sender_counts = Counter(msg.get('sender', 'Unknown sender') for msg in messages)

    return {
        "labels": list(sender_counts.keys()),
        "values": list(sender_counts.values())
    }


# Dictionary of chart generators
CHART_GENERATORS: Dict[str, ChartGenerator] = {
    "sender_activity": sender_activity_chart
}


def generate_chart_data(messages: List[Dict[str, Any]], chart_type: str) -> JSONResponse:
    """Dispatcher for creating chart data."""
    if not messages:
        return JSONResponse(content={"labels": [], "values": []})

    generator = CHART_GENERATORS.get(chart_type)
    if not generator:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported chart type: {chart_type}",
                "available_types": list(CHART_GENERATORS.keys())
            }
        )

    try:
        chart_data = generator(messages)
        return JSONResponse(content=chart_data)
    except Exception as e:
        logger.error(f"Error creating chart '{chart_type}': {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create data for chart '{chart_type}'"}
        )