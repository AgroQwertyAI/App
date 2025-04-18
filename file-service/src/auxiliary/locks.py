import asyncio

# Create a dedicated lock for Excel file operations
excel_file_lock = asyncio.Lock() 