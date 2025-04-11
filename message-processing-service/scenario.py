import json

from llm import chat

STRAGEGY = "CSV"
MODEL_NAME = "Mistral"

async def agentic(history: list, message: str) -> bool:
    
    payload = history
    
    
    if len(history) == 0:
        
    
        payload = [
            {
                "role": "system",
                "content": f"Ты - {MODEL_NAME}, добрый и позитивный агент в системе обработки аграномичских сообщений. Твоя задача - общаться с пользователям и сказать что если ему нужно поделиться отчетом, нужно просто отправить его в этот чат в текстовом виде, изображении или голосового сообщения. Тебе не нужно отвечать за обработку, другой агент займется ей автоматически при получении отчёта."  
            },
            {
                "role": "user",
                "content": f"{message}"
            }
        ]
    else:
        payload.append({ "role": "user", "content": f"{message}" })
    
    result = await chat("mist", payload)
    result = result.choices[0].message.content
    
    payload.append({ "role": "assistant", "content": result })
    
    return {"history": payload, "answer": result}

async def is_report(message: str) -> bool:
    payload = [
        {
            "role": "system",
            "content": f"Ты - {MODEL_NAME}, очень точная и интеллектуальная модель классификации агрономисеских отчётов. Тебе будет дано сообщение из чата и всё что тебе нужно сделать это определить является ли оно агрономическим отчётом. Агрономический отчет - сообщение в свободной форме с информацией о каких-то операциях на полях. Подумай и если это сообщение является отчётом, наипши 'REPORT', если оно не является отчётом, например , 'TALK'."  
        },
        {
            "role": "user",
            "content": f"Вот сообщение, которое тебе необходимо классифицировать: {message}"
        }
    ]
    
    result = await chat("mist", payload)
    result = result.choices[0].message.content
    
    return 'REPORT' in result

async def extract_data_from_message(message: str) -> dict:
    result = ""
    
    if STRAGEGY == "CSV":
        result = await extract_csv(message)
        
    return result

async def extract_csv(message: str) -> dict:
    payload = [
        {
            "role": "system",
            "content": f"Ты - {MODEL_NAME}, очень точная и интеллектуальная модель. Тебе будет дано сообщение из агрономического чата и твоя задача подумать и выделить из неё нужную информацию для того чтобы вывести её в строгом формате .csv файла с разделителем ';'. В конце ответа, помести итоговый .csv файл в блок ```csv\n<CSV таблица здесь```. Нужно использовать точно такое описание таблицы и не пропускать колонки: {format_table_definition_for_llm('default_table_definition.json')}. Важно: некоторые поля могут быть пустыми. Если в сообщении нет информации для ячеек \"Подразделение, Операция, Культура\" (остальные поля могут быть пустыми), тебе нужно задать дополнительный вопрос для отправителя сообщения в блоке ```message\n<Сообщение здесь>```\n\n"  
        },
        {
            "role": "user",
            "content": f"Вот сообщение, которое тебе необходимо обработать: {message}"
        }
    ]
    
    result = await chat("mist", payload)
    result = result.choices[0].message.content
    
    csv_data = None
    data = []
    if "```csv" in result:
        parts = result.split("```csv\n", 1)
        if len(parts) > 1:
            csv_block = parts[1].split("```", 1)[0]
            csv_data = csv_block.strip()
            
            if csv_data:
                lines = csv_data.strip().split('\n')
                headers = lines[0].split(';') if lines else []
                
                for line_idx in range(1, len(lines)):
                    values = lines[line_idx].split(';')
                    row_data = {}
                    for i in range(min(len(headers), len(values))):
                        row_data[headers[i]] = values[i]
                    data.append(row_data)
    
    question = None
    if "```message" in result:
        parts = result.split("```message\n", 1)
        if len(parts) > 1:
            message_block = parts[1].split("```", 1)[0]
            question = message_block.strip()
    
    if question == "": question = None
    
    return {
        "data": data,
        "question": question,
        "success": len(data) > 0
    }
    
    
    
def format_table_definition_for_llm(table_definition):
    """
    Преобразует JSON-определение таблицы в форматированную строку для обработки LLM.
    
    Аргументы:
        table_definition (dict или str): Распарсенный JSON-объект или путь к JSON-файлу
        
    Возвращает:
        str: Форматированная строка с описанием структуры таблицы
    """
    
    
    if isinstance(table_definition, str):
        try:
            with open(table_definition, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            return f"Ошибка загрузки JSON-файла: {str(e)}"
    else:
        data = table_definition
    
    output = "Определение таблицы:\n\n"
    
    if 'fields' in data:
        for field in data['fields']:
            output += f"Столбец: {field.get('name', 'Без имени')}\n"
            output += f"Описание: {field.get('description', 'Нет описания')}\n"
            
            if 'possible_values' in field:
                if isinstance(field['possible_values'], list):
                    values = ', '.join(field['possible_values'])
                    output += f"Возможные значения: {values}\n"
                else:
                    output += f"Возможные значения: {field['possible_values']}\n"
            
            output += f"Обязательно?: {field['required']}\n"
            
            output += "\n"
    
    return output