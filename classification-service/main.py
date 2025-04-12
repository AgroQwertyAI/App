import os
import logging
from typing import List, Optional

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import BertTokenizerFast
from dotenv import load_dotenv
import gc

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
API_PORT = int(os.getenv("API_PORT", 52004))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 16))  # Оптимальный размер батча для 4ГБ видеокарты

# Инициализация FastAPI
app = FastAPI(
    title="Classification Service",
    description="Сервис для классификации сообщений с использованием BERT модели",
    version="0.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация модели
MODEL_NAME = "AgroQwertyAI/berta_report_classifier_onnx"
ID2LABEL = {0: "другое", 1: "отчёт"}
LABEL2ID = {"другое": 0, "отчёт": 1}

# Определение доступных провайдеров
available_providers = ort.get_available_providers()
logger.info(f"Доступные провайдеры ONNX: {available_providers}")

# Настройка провайдеров с приоритетом TensorRT, затем CUDA, затем CPU
preferred_providers = []

# Проверяем доступность TensorRT
if "TensorrtExecutionProvider" in available_providers:
    # Настройка TensorRT для оптимизации вывода
    tensorrt_options = {
        'device_id': 0,                       # Выбор GPU для выполнения
        'trt_max_workspace_size': 2147483648, # Установка лимита использования памяти GPU (2GB)
        'trt_fp16_enable': True,              # Включение FP16 для более быстрого вывода
    }
    preferred_providers.append(("TensorrtExecutionProvider", tensorrt_options))
    logger.info("TensorRT будет использоваться для инференса")

# Добавляем CUDA как запасной вариант
if "CUDAExecutionProvider" in available_providers:
    cuda_options = {
        'device_id': 0,
        'arena_extend_strategy': 'kNextPowerOfTwo',
        'gpu_mem_limit': 3 * 1024 * 1024 * 1024,  # 2GB лимит памяти
        'cudnn_conv_algo_search': 'EXHAUSTIVE',    # Более тщательный поиск оптимального алгоритма
        'do_copy_in_default_stream': True,
    }
    preferred_providers.append(("CUDAExecutionProvider", cuda_options))
    if "TensorrtExecutionProvider" not in available_providers:
        logger.info("CUDA будет использоваться для инференса (TensorRT недоступен)")

# Если ни TensorRT, ни CUDA недоступны
if not preferred_providers:
    logger.warning("GPU ускорители недоступны, будет использоваться CPU")

# Всегда добавляем CPU как запасной вариант
preferred_providers.append("CPUExecutionProvider")

# Создание сессии с оптимизированными настройками
session_options = ort.SessionOptions()
session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
session_options.enable_mem_pattern = True
session_options.intra_op_num_threads = 4

# Инициализация токенизатора
tokenizer = BertTokenizerFast.from_pretrained("AgroQwertyAI/berta_report_classifier")

# Инициализация сессии ONNX с оптимизированными настройками
model_path = os.path.join("model", "model.onnx")
ort_session = ort.InferenceSession(model_path, sess_options=session_options, providers=preferred_providers)

# Логируем активный провайдер
active_provider = ort_session.get_providers()[0]
logger.info(f"Активный провайдер для инференса: {active_provider}")


# Модели данных
class ClassificationRequest(BaseModel):
    text: str = Field(..., description="Текст для классификации")
    threshold: Optional[float] = Field(0.5, description="Порог вероятности для класса 'отчёт'")


class BatchClassificationRequest(BaseModel):
    texts: List[str] = Field(..., description="Список текстов для классификации")
    threshold: Optional[float] = Field(0.5, description="Порог вероятности для класса 'отчёт'")


class ClassificationResponse(BaseModel):
    label: str = Field(..., description="Метка классификации ('отчёт' или 'другое')")
    confidence: float = Field(..., description="Уверенность модели в предсказании")


class BatchClassificationResponse(BaseModel):
    results: List[ClassificationResponse]


async def classify_text(text: str, threshold: float = 0.5) -> ClassificationResponse:
    """Классифицирует текст с использованием модели ONNX."""
    try:
        # Токенизация входного текста
        inputs = tokenizer(
            text,
            truncation=True,
            max_length=512,
            return_tensors="np"
        )

        # Получение входов модели
        ort_inputs = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
            "token_type_ids": inputs["token_type_ids"]
        }

        # Выполнение инференса
        logits = ort_session.run(None, ort_inputs)[0]

        # Преобразование логитов в вероятности с помощью softmax
        probabilities = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)
        confidence = float(probabilities[0][1])  # Вероятность класса "отчёт"

        # Определение метки на основе порога
        label = "отчёт" if confidence >= threshold else "другое"

        return ClassificationResponse(label=label, confidence=confidence)
    except Exception as e:
        logger.error(f"Ошибка при классификации текста: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка классификации: {str(e)}")


@app.post("/classify", response_model=ClassificationResponse)
async def classify_endpoint(request: ClassificationRequest):
    """Эндпоинт для классификации одного текста."""
    return await classify_text(request.text, request.threshold)


@app.post("/classify_batch", response_model=BatchClassificationResponse)
async def classify_batch_endpoint(request: BatchClassificationRequest):
    """Эндпоинт для пакетной классификации текстов с оптимизацией для GPU."""
    results = []

    # Обрабатываем тексты батчами для оптимизации работы GPU
    for i in range(0, len(request.texts), BATCH_SIZE):
        batch_texts = request.texts[i:i + BATCH_SIZE]
        try:
            # Токенизация всех текстов в батче за один вызов
            inputs = tokenizer(
                batch_texts,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="np"
            )

            # Получение входов модели
            ort_inputs = {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"],
                "token_type_ids": inputs["token_type_ids"]
            }

            # Выполнение инференса для батча
            logits = ort_session.run(None, ort_inputs)[0]

            # Преобразование логитов в вероятности с помощью softmax
            probabilities = np.exp(logits) / np.sum(np.exp(logits), axis=1, keepdims=True)

            # Формирование результатов для текущего батча
            for j, prob in enumerate(probabilities):
                confidence = float(prob[1])  # Вероятность класса "отчёт"
                label = "отчёт" if confidence >= request.threshold else "другое"
                results.append(ClassificationResponse(label=label, confidence=confidence))

            # Явно освобождаем память после каждого батча
            del inputs, ort_inputs, logits, probabilities
            if "CUDAExecutionProvider" in active_provider:
                gc.collect()

        except Exception as e:
            logger.error(f"Ошибка при обработке батча {i}-{i + BATCH_SIZE}: {str(e)}")
            # Если произошла ошибка при обработке батча, обрабатываем тексты по отдельности
            for text in batch_texts:
                try:
                    result = await classify_text(text, request.threshold)
                    results.append(result)
                except Exception as inner_e:
                    logger.error(f"Ошибка при обработке отдельного текста: {str(inner_e)}")
                    results.append(ClassificationResponse(label="ошибка", confidence=0.0))

    return BatchClassificationResponse(results=results)


@app.get("/health")
async def health_check():
    """Эндпоинт проверки работоспособности сервиса."""
    device_info = "GPU" if "CUDAExecutionProvider" in active_provider else "CPU"
    memory_info = {}

    # Если используется CUDA, пробуем получить информацию о памяти
    if "CUDAExecutionProvider" in active_provider:
        try:
            import subprocess
            nvidia_smi = subprocess.check_output("nvidia-smi --query-gpu=memory.used,memory.total --format=csv",
                                                 shell=True)
            memory_info = {"gpu_info": nvidia_smi.decode("utf-8").strip()}
        except:
            memory_info = {"gpu_info": "Не удалось получить информацию о памяти GPU"}

    return {
        "status": "ok",
        "model": MODEL_NAME,
        "provider": active_provider,
        "device": device_info,
        "batch_size": BATCH_SIZE,
        "memory": memory_info
    }


if __name__ == "__main__":
    import uvicorn

    # Проверяем, существует ли модель, иначе выводим инструкцию по загрузке
    if not os.path.exists(model_path):
        logger.error("Модель не найдена! Создайте директорию 'model' и загрузите файл model.onnx")
        logger.info("Для загрузки модели из Hugging Face выполните команду:")
        logger.info(
            "python -c \"from huggingface_hub import hf_hub_download; hf_hub_download('AgroQwertyAI/berta_report_classifier_onnx', 'model.onnx', local_dir='model')\"")
    else:
        # Запуск сервера
        uvicorn.run("main:app", host="0.0.0.0", port=API_PORT, reload=False)  # reload=False для стабильной работы с GPU