import asyncio

import json

from src.llm import chat

from src.bert import is_report_bert

from src.online_log import log

STRAGEGY = "CSV"
MODEL_NAME = "Mistral"

async def agentic(history: list, message: str):
    
    payload = history
    
    
    if len(history) == 0:
        
    
        payload = [
            {
                "role": "system",
                "content": f"Ты - {MODEL_NAME}, добрый и позитивный агент в системе обработки аграномичских сообщений. Твоя задача - общаться с пользователям и сказать что если ему нужно поделиться отчетом, нужно просто отправить его в этот чат в текстовом виде, изображении или голосового сообщения. Тебе не нужно отвечать за обработку, другой агент займется ей автоматически при получении отчёта."  
            },
            {
                "role": "user",
                "content": f"Таблица которую нужно проверить:\n```csv\n{message}```"
            }
        ]
    else:
        payload.append({ "role": "user", "content": f"{message}" })
    
    result = await chat("yagpt", payload)
    result = result.choices[0].message.content
    
    payload.append({ "role": "assistant", "content": result })
    
    return {"history": payload, "answer": result}

async def is_report(message: str, use_bert: bool = False) -> bool:
    if use_bert:
        from bert import is_report_bert
        return await is_report_bert(message)
    
    payload = [
        {
            "role": "system",
            "content": f"Ты - {MODEL_NAME}, очень точная и интеллектуальная модель классификации агрономических отчётов. Тебе будет дано сообщение из чата и всё что тебе нужно сделать это определить является ли оно агрономическим отчётом. Агрономический отчет - сообщение в свободной форме с информацией о каких-то операциях на полях. Подумай и если это сообщение является отчётом, напиши 'REPORT', если оно не является отчётом, напиши 'TALK'.\nПримеры отчётов:\n1)\nСевер \nОтд7 пах с св 41/501\nОтд20 20/281 по пу 61/793\nОтд 3 пах подс.60/231\nПо пу 231\n\nДиск к. Сил отд 7. 32/352\nПу- 484\nДиск под Оз п езубов 20/281\nДиск под с. Св отд 10 83/203 пу-1065га\n\n2)\nПривет, по отделу 7 прошлись пахотой сах свеклы 41/501.\n\nИ другие. Если сообщение хоть как-то похоже на агрономический отчёт, пиши 'REPORT'."  
        },
        {
            "role": "user",
            "content": f"Вот сообщение, которое тебе необходимо классифицировать: {message}"
        }
    ]
    
    result = await chat("yagpt", payload)
    result = result.choices[0].message.content
    
    return 'REPORT' in result

async def split_report(message: str, prompt = None) -> list:
    instr = f"Пользователь даст тебе отчёт из чата и перед тобой стоит задача разделить его по операциям. Исходный формат в свободном стиле и может иметь сокращения. Вот возможные операции: 1-я междурядная культивация, 2-я междурядная культивация, Боронование довсходовое, Внесение минеральных удобрений, Выравнивание зяби, 2-е Выравнивание зяби, Гербицидная обработка, 1 Гербицидная обработка, 2 Гербицидная обработка, 3 Гербицидная обработка, 4 Гербицидная обработка, Дискование, Дискование 2-е, Инсектицидная обработка, Культивация, Пахота, Подкормка, Предпосевная культивация, Прикатывание посевов, Сев, Сплошная культивация, Уборка, Функицидная обработка, Чизлевание. Твоя задача - вывести списком разделенные по операциям сообщения. Для каждой операции из исходного сообщения нужно в точности переписать все относящиеся к нему данные. Если в сообщении была информация относящаяся ко всем операциям - дата для всех сообщений или название подразделений, тебе нужно переписать их в дополнении к каждому разделенному сообщению с операцией. Некоторые операции могут быть не полными и содержать не все поля. Внимание, формат вывода: тебе нужно вывести результат в качестве json обьекта с полем separated_reports типа массива строк. Json должен быть корректным для парсинга. Не выводи никакой разметки кроме корректного json."
    if prompt:
        instr =  prompt
    
    payload = [
        {
            "role": "system",
            "content":   instr
        },
        {
            "role": "user",
            "content": f"Вот сообщение, которое тебе необходимо разделить: {message}"
        }
    ]
    
    structure = {
        "type": "object",
        "properties": {
            "separated_reports": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["separated_reports"]
    }
    
    result = await chat("yagpt", payload, structure=structure)
    try:
        content = result.choices[0].message.content
        # In case LLM returns text before or after the JSON
        if '{' in content and '}' in content:
            json_part = content[content.find('{'):content.rfind('}')+1]
            parsed_result = json.loads(json_part)
        else:
            parsed_result = json.loads(content)
            
        return parsed_result.get("separated_reports", [])
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw content: {result.choices[0].message.content}")
        return []



async def extract_data_from_message(message: str, template: dict) -> dict:
    result = []
    
    print("TASK SPLIT PROMPT", template.get("taskSplitPrompt"))
    
    split = await split_report(message, template.get("taskSplitPrompt"))
    log(f"Task split result: {split}", level="info", source="split_report")
    
    tasks = [extract_csv(msg, template.get("systemPrompt")) for msg in split]
    result = await asyncio.gather(*tasks)
    
    return result

async def determine_questions(table: str) -> dict:
    payload = [
        {
            "role": "system",
            "content": "Твоя задача определить, есть ли в таблице ошибки, и если есть, то сформулировать вопрос к пользователю, с запросом дополнительных данных. Убедись, что во всех строках таблицы заполнены обязательные поля. Список обязательных полей: \"Подразделение\" (Название подразделения. Возможные значения - АОР, ТСК, АО Кропоткинское, Восход, Колхоз, Мир, СП Коломейцево), \"Операция\", \"Культура\", \"За день, га\", \"С начала операции, га\". Другие поля могут быть пустыми. В ответе ты должен вывести только вопрос. Можешь говорить к каким строчкам таблицы относятся вопросы."
        },
        {
            "role": "user",
            "content": table
        }
    ]
    
    result = await chat("yagpt", payload)
    return result.choices[0].message.content
        

async def get_history_for_followup(table: str, assistant_message: str) -> dict:
    payload = [
        {
            "role": "system",
            "content": "Твоя задача исправить таблицу, получив ответы на дополнительные вопросы, чтобы исправить проблемы. Когда пользователь даст ответы на все вопросы, тебе нужно вывести итоговую исправленную таблицу в формате ```csv\n<таблица здесь```. Убедись, что во всех строках таблицы заполнены обязательные поля и они исползьуют допустимые значения: \"Подразделение\" (Название подразделения. Возможные значения - АОР, ТСК, АО Кропоткинское, Восход, Колхоз, Мир, СП Коломейцево), \"Операция\", \"Культура\", \"За день, га\", \"С начала операции, га\". Другие поля могут быть пустыми. Если пользователь не предоставил ответы на вопросы, ты можешь переспросить."
        },
        {
            "role": "user",
            "content": table
        },
        {
            "role": "assistant",
            "content": assistant_message
        }
    ]
    
    return payload

async def extract_csv(message: str, prompt = None) -> dict:
    inst = open('prompt.txt', encoding='utf-8').read()
    
    if prompt:
        inst = prompt
    
    payload = [
        {
            "role": "system",
            "content": inst
        },
        {
            "role": "user",
            "content": f"Вот сообщение, которое тебе необходимо обработать: {message}"
        }
    ]
    
    result = await chat("yagpt", payload)
    result = result.choices[0].message.content
    
    print(result)
    
    
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
    if "```question" in result:
        parts = result.split("```question", 1)
        if len(parts) > 1:
            message_block = parts[1].split("```", 1)[0]
            question = message_block.strip()
    
    if question == "": question = None
    
    result_dict = {
        "data": data,
        "question": question,
        "success": len(data) > 0
    }
    
    log(f"Extracted CSV data: {result_dict}", level="info", source="extract_csv")
    
    return result_dict
    
    
    
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