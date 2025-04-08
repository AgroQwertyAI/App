import os
from src.schemas import CronJob, CronArgs
from src.settings import generator_service_url
import aiohttp
from fastapi import HTTPException
from datetime import datetime

def get_command(job: CronJob) -> str:
    return f"uv run {os.path.dirname(__file__)}/scripts/save.py {job.folder_name} {job.format} {job.chat_id} {job.type}"

def get_schedule(job: CronJob) -> str:
    return f"{job.minute} {job.hour} {job.day_of_month} {job.month} {job.day_of_week}"

def get_full_record(job: CronJob) -> str:
    return f"{get_schedule(job)} {get_command(job)}"

async def get_data(cron_args: CronArgs) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{generator_service_url}/api/services/generate_table?chat_id={cron_args.chat_id}&format={cron_args.format}") as response:
            if response.status != 200:
                raise HTTPException(500, detail=f"Failed to generate table: {response.status}")
            return await response.text()

def save_data_to_filesystem(cron_args: CronArgs, data: str):
    current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    with open(f"{os.path.dirname(__file__)}/{cron_args.folder_name}/{current_time}.{cron_args.format}", "w") as f:
        f.write(data)
