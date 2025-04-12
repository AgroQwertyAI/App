import asyncio
import aiohttp
import time
import random
import argparse
import json
from typing import List, Dict, Any, Optional

# Примеры текстов для классификации
TEST_TEXTS = [
    "Вчера я посмотрел отличный фильм, всем рекомендую.",
    "Отчет содержит следующие разделы: введение, методология, результаты и выводы.",
    "Статистические данные указывают на рост показателей на 12% по сравнению с прошлым годом.",
    "Завтра состоится важная встреча в конференц-зале.",
    "Согласно отчету аналитического отдела, эффективность работы возросла на 15%.",
    "Я купил новый телефон, очень доволен покупкой.",
    "Отчет о проделанной работе за второй квартал 2023 года показал положительную динамику.",
    "Количество обработанных заявок в марте составило 453 единицы.",
    "Сегодня хорошая погода, думаю пойти погулять в парке.",
    "В соответствии с пунктом 3.4 регламента необходимо утвердить бюджет на следующий квартал.",
]


async def send_single_request(session: aiohttp.ClientSession, url: str, text: str, request_id: int) -> Dict[str, Any]:
    """Отправляет один запрос к API классификации"""
    start_time = time.time()
    try:
        async with session.post(url, json={"text": text, "threshold": 0.5}) as response:
            elapsed = time.time() - start_time
            if response.status == 200:
                result = await response.json()
                return {
                    "request_id": request_id,
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "status": response.status,
                    "result": result,
                    "elapsed_time": elapsed,
                    "success": True
                }
            else:
                error_text = await response.text()
                return {
                    "request_id": request_id,
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "status": response.status,
                    "error": error_text,
                    "elapsed_time": elapsed,
                    "success": False
                }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "request_id": request_id,
            "text": text[:50] + "..." if len(text) > 50 else text,
            "error": str(e),
            "elapsed_time": elapsed,
            "success": False
        }


async def send_batch_request(session: aiohttp.ClientSession, url: str, texts: List[str], batch_id: int) -> List[
    Dict[str, Any]]:
    """Отправляет пакетный запрос к API классификации"""
    start_time = time.time()
    try:
        async with session.post(url, json={"texts": texts, "threshold": 0.5}) as response:
            elapsed = time.time() - start_time
            if response.status == 200:
                batch_result = await response.json()
                results = []
                for i, (text, result) in enumerate(zip(texts, batch_result["results"])):
                    results.append({
                        "request_id": f"{batch_id}-{i + 1}",
                        "text": text[:50] + "..." if len(text) > 50 else text,
                        "status": response.status,
                        "result": result,
                        "elapsed_time": elapsed / len(texts),  # Приблизительное время на один запрос
                        "batch_time": elapsed,
                        "success": True
                    })
                return results
            else:
                error_text = await response.text()
                return [{
                    "request_id": f"{batch_id}-batch",
                    "texts_count": len(texts),
                    "status": response.status,
                    "error": error_text,
                    "elapsed_time": elapsed,
                    "success": False
                }]
    except Exception as e:
        elapsed = time.time() - start_time
        return [{
            "request_id": f"{batch_id}-batch",
            "texts_count": len(texts),
            "error": str(e),
            "elapsed_time": elapsed,
            "success": False
        }]


async def run_concurrent_single_requests(url: str, num_requests: int, texts: List[str] = None, concurrency: int = 10) -> \
List[Dict[str, Any]]:
    """Запускает несколько одиночных запросов с заданным уровнем параллелизма"""
    if texts is None or len(texts) < num_requests:
        # Генерируем или дополняем тексты, если их недостаточно
        texts = (texts or []) + [random.choice(TEST_TEXTS) for _ in range(max(0, num_requests - len(texts or [])))]
    elif len(texts) > num_requests:
        texts = texts[:num_requests]

    results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_request(session, url, text, req_id):
        async with semaphore:
            return await send_single_request(session, url, text, req_id)

    async with aiohttp.ClientSession() as session:
        tasks = [bounded_request(session, url, texts[i], i + 1) for i in range(num_requests)]
        return await asyncio.gather(*tasks)


async def run_batch_requests(url: str, num_requests: int, batch_size: int, texts: List[str] = None) -> List[
    Dict[str, Any]]:
    """Запускает пакетные запросы"""
    if texts is None or len(texts) < num_requests:
        # Генерируем или дополняем тексты, если их недостаточно
        texts = (texts or []) + [random.choice(TEST_TEXTS) for _ in range(max(0, num_requests - len(texts or [])))]
    elif len(texts) > num_requests:
        texts = texts[:num_requests]

    # Разделяем тексты на батчи
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]

    all_results = []
    async with aiohttp.ClientSession() as session:
        for i, batch in enumerate(batches):
            batch_results = await send_batch_request(session, url, batch, i + 1)
            all_results.extend(batch_results)

    return all_results


def print_results(results: List[Dict[str, Any]], use_batches: bool = False) -> None:
    """Выводит результаты тестирования в читаемом формате"""
    print("\n==== РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ====")

    # Общая статистика
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    failed = total - successful

    # Время выполнения
    times = [r.get("batch_time", r["elapsed_time"]) for r in results if "elapsed_time" in r]
    avg_time = sum(times) / len(times) if times else 0
    min_time = min(times) if times else 0
    max_time = max(times) if times else 0

    print(f"\nВсего обработано: {total} запросов")
    print(f"Успешных запросов: {successful}")
    print(f"Неудачных запросов: {failed}")
    print(f"\nСреднее время выполнения: {avg_time:.4f} сек")
    print(f"Минимальное время: {min_time:.4f} сек")
    print(f"Максимальное время: {max_time:.4f} сек")

    if use_batches:
        batch_times = [r.get("batch_time") for r in results if "batch_time" in r]
        if batch_times:
            print(f"\nСреднее время на батч: {sum(batch_times) / len(batch_times):.4f} сек")

    # Покажем первые 10 результатов для краткости
    print("\n--- Примеры результатов (первые 10) ---")
    for r in results[:10]:
        print(f"\nЗапрос #{r['request_id']}")
        if "text" in r:
            print(f"Текст: {r['text']}")
        elif "texts_count" in r:
            print(f"Количество текстов в батче: {r['texts_count']}")

        print(f"Время выполнения: {r['elapsed_time']:.4f} сек")

        if r.get("success", False):
            print(f"Статус: {r['status']} (успешно)")
            if "result" in r:
                label = r['result']['label'] if isinstance(r['result'], dict) else "Нет данных"
                confidence = r['result'].get('confidence', 0) if isinstance(r['result'], dict) else 0
                print(f"Класс: {label}, Уверенность: {confidence:.4f}")
        else:
            print(f"Статус: {r.get('status', 'Ошибка')} (неудачно)")
            print(f"Ошибка: {r.get('error', 'Неизвестная ошибка')}")

    # Сохраняем полные результаты в файл
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nПолные результаты сохранены в файл test_results.json")


async def main():
    parser = argparse.ArgumentParser(description='Тестирование API классификации')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Хост сервера')
    parser.add_argument('--port', type=int, default=52004, help='Порт сервера')
    parser.add_argument('--requests', type=int, default=500, help='Количество запросов')
    parser.add_argument('--concurrency', type=int, default=1000, help='Уровень параллелизма (для одиночных запросов)')
    parser.add_argument('--batch', action='store_true', help='Использовать пакетные запросы')
    parser.add_argument('--batch-size', type=int, default=16, help='Размер батча (для пакетных запросов)')

    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    single_url = f"{base_url}/classify"
    batch_url = f"{base_url}/classify_batch"

    print(f"Запуск тестирования на {base_url}")
    print(f"Количество запросов: {args.requests}")

    start_time = time.time()

    if args.batch:
        print(f"Режим: пакетная обработка (размер батча: {args.batch_size})")
        results = await run_batch_requests(batch_url, args.requests, args.batch_size)
    else:
        print(f"Режим: одиночные запросы (параллелизм: {args.concurrency})")
        results = await run_concurrent_single_requests(single_url, args.requests, concurrency=args.concurrency)

    total_time = time.time() - start_time

    print_results(results, use_batches=args.batch)
    print(f"\nОбщее время выполнения теста: {total_time:.4f} сек")
    print(f"RPS (запросы в секунду): {args.requests / total_time:.2f}")


if __name__ == "__main__":
    asyncio.run(main())