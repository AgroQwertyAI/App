import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)



def generate_table_image(result: List[Dict[str, Any]]) -> str:
    """
    Generate a PNG image of a table from the result dictionary and return it as a
    base64-encoded data URL.
    
    Args:
        result: List of dictionaries containing data, question, and success fields
        
    Returns:
        A string containing a data URL with the base64-encoded PNG image
    """
    try:
        # Extract data rows from results
        all_data = []
        for item in result:
            if item.get('success', False) and item.get('data'):
                for data_item in item.get('data', []):
                    # Clean up data item (replace None/null values with empty strings)
                    cleaned_item = {k: (v if v is not None else '') for k, v in data_item.items()}
                    all_data.append(cleaned_item)

        # If no valid data, return empty string
        if not all_data:
            logger.warning("No valid data found to generate table image")
            return ""
        
        # Create DataFrame from data
        df = pd.DataFrame(all_data)
        
        # Replace NaN with empty strings for display
        df = df.fillna('')
        
        # Determine figure size based on data
        rows, cols = df.shape
        fig_width = min(14, max(8, cols * 1.5))  # Adjust based on column count
        fig_height = min(10, max(4, rows * 0.5))  # Adjust based on row count
        
        # Create figure and axis
        fig = Figure(figsize=(fig_width, fig_height), dpi=100)
        ax = fig.add_subplot(111)
        
        # Hide axes
        ax.axis('off')
        
        # Create the table and add it to the axis
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            cellLoc='center',
            loc='center',
            colColours=['#f2f2f2'] * len(df.columns)
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)  # Adjust row height
        
        # Make the table fit the figure
        table.auto_set_column_width(col=list(range(len(df.columns))))
        
        # Render to PNG
        buf = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.draw()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2)
        buf.seek(0)
        
        # Convert PNG to base64
        img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Return as data URL
        return f"data:image/png;base64,{img_str}"
    
    except Exception as e:
        logger.error(f"Error generating table image: {str(e)}")
        return ""


def dict_to_csv_string(result: List[Dict[str, Any]]) -> str:
    """
    Convert the structured result dictionary to a CSV string.
    
    Args:
        result: List of dictionaries containing data, question, and success fields
        
    Returns:
        A string containing the data in CSV format
    """
    try:
        # Extract data rows from successful results
        all_data = []
        for item in result:
            if item.get('success', False) and item.get('data'):
                all_data.extend(item.get('data', []))

        # If no valid data, return empty string
        if not all_data:
            logger.warning("No valid data found to convert to CSV")
            return ""
        
        # Normalize column names by removing extra spaces
        normalized_data = []
        for row in all_data:
            normalized_row = {}
            for key, value in row.items():
                # Normalize key by removing extra spaces
                normalized_key = ' '.join(key.split())
                # Replace None with empty string
                normalized_value = '' if value is None else value
                normalized_row[normalized_key] = normalized_value
            normalized_data.append(normalized_row)
        
        # Create DataFrame from normalized data
        df = pd.DataFrame(normalized_data)
        
        # Replace NaN values with empty strings
        df = df.fillna('')
        
        # Convert DataFrame to CSV string
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        
        return csv_string
    
    except Exception as e:
        logger.error(f"Error converting data to CSV: {str(e)}")
        return ""


def extract_questions(result: List[Dict[str, Any]]) -> str:
    """
    Extract all questions from the result dictionary and format them as a 
    numbered list in Russian, indicating which line they are for.
    
    Args:
        result: List of dictionaries containing data, question, and success fields
        
    Returns:
        A string containing numbered questions in Russian, or empty string if no questions
    """
    try:
        questions = []
        
        # Russian ordinal number suffixes
        def get_russian_ordinal(n):
            if n == 1:
                return "1-й"
            elif n == 2:
                return "2-й"
            elif n == 3:
                return "3-й"
            else:
                return f"{n}-й"
        
        # Extract all questions with their data context
        for i, item in enumerate(result, 1):
            question = item.get('question')
            
            if question and isinstance(question, str):
                # Get a short description of the data to refer to
                data_desc = ""
                
                questions.append(f"Вопрос по строке номер {i}: {question}")
        
        if not questions:
            return ""
        
        # Join all questions with line breaks
        return "\n".join(questions)
    
    except Exception as e:
        logger.error(f"Error extracting questions: {str(e)}")
        return ""
    

def parse_table_from_message(message: str) -> list[dict]:
    """
    Extracts and parses a CSV table from a message enclosed in either ```csv or <table> tags.
    
    Args:
        message: The message text containing a CSV table
        
    Returns:
        A list of dictionaries, where each dictionary represents a row in the table
        
    Example:
        Input with a table between tags will return:
        [{'Дата': '', 'Подразделение': 'АОР', 'Операция': 'Пахота', ...}]
    """
    import re
    import csv
    from io import StringIO
    
    # Try different tag patterns
    patterns = [
        r"```csv\n(.*?)\n```",
        r"<table>\n(.*?)\n</table>"
    ]
    
    csv_content = None
    for pattern in patterns:
        match = re.search(pattern, message, re.DOTALL)
        if match:
            csv_content = match.group(1)
            break
    
    if not csv_content:
        return []
    
    # Try to detect the delimiter
    first_line = csv_content.split('\n')[0]
    if ',' in first_line:
        delimiter = ','
    elif '\t' in first_line:
        delimiter = '\t'
    elif ';' in first_line:
        delimiter = ';'
    else:
        delimiter = ','  # Default to comma
    
    try:
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        # Convert to list of dictionaries
        result = []
        for row in reader:
            # Create a clean dict with trimmed keys and values
            cleaned_row = {k.strip(): v.strip() if v and v.strip() else '' 
                          for k, v in row.items() if k}
            result.append(cleaned_row)
        
        return result
    except Exception as e:
        logging.error(f"Error parsing CSV table: {str(e)}")
        return []

