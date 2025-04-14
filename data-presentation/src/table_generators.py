import io
import logging
from typing import List, Dict, Any, Protocol
from enum import Enum

import pandas as pd
from fastapi.responses import StreamingResponse, JSONResponse, Response


# Base types
class TableFormat(str, Enum):
    xlsx = "xlsx"
    csv = "csv"
    json = "json"


# Logger setup
logger = logging.getLogger(__name__)



def create_dataframe_from_data(messages: List[Dict[str, Any]], columns: List[str]) -> pd.DataFrame:
    """Creates a DataFrame directly from message data fields."""
    if not messages:
        return pd.DataFrame(columns=columns)

    # Extract all data items from messages
    records = []
    for msg in messages:
        data_items = msg.get('data', [])
        if isinstance(data_items, list):
            records.extend(data_items)
        elif isinstance(data_items, dict):
            records.append(data_items)

    # Create DataFrame
    df = pd.DataFrame(records)

    # Ensure presence of all requested columns
    for col in columns:
        if col not in df.columns:
            df[col] = None

    # Select only the requested columns if specified
    if columns:
        existing_columns = [col for col in columns if col in df.columns]
        df = df[existing_columns]

    return df


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
