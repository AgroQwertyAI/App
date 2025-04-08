from fastapi import FastAPI
from crontab import CronTab
from pydantic import BaseModel
from typing import List
from src.schemas import CronJob
import logging
from src.auxiliary import get_command, get_schedule
from src.settings import api_port
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="File Service",
    description="A service for saving files.",
    version="0.1.0",

)

class CronJobsResponse(BaseModel):
    cron_jobs: List[str]

@app.get("/api/jobs", response_model=list[CronJob])
async def get_jobs():
    logger.info("Getting jobs")
    try:
        cron = CronTab(user=True)
        for job in cron:
            arguments = job.command.split(" ")
            folder_name = arguments[3]
            format = arguments[4]
            chat_id = arguments[5]
            type = arguments[6]

            minute = job.minute
            hour = job.hour
            day_of_month = job.day
            month = job.month
            day_of_week = job.dow

            cron_jobs.append(CronJob(
                folder_name=folder_name,
                format=format,
                chat_id=chat_id,
                type=type,
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month=month,
                day_of_week=day_of_week
            ))

        logger.info(f"Found {len(cron_jobs)} jobs")
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        cron_jobs = []
    return cron_jobs

@app.post("/api/job")
async def create_job(job: CronJob):
    logger.info(f"Creating job: {job}")
    try:
        command = get_command(job)
        schedule = get_schedule(job)
        cron = CronTab(user=True)
        job = cron.new(command=command)
        job.setall(schedule)
        
        cron.write()

        logger.info(f"Job created: {job}")
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise

@app.delete("/api/job")
async def delete_job(job_delete: CronJob):
    logger.info(f"Deleting job: {job_delete}")
    try:
        cron = CronTab(user=True)
        for job in cron:
            if (
                job.command == get_command(job_delete),
                job.minute == job_delete.minute,
                job.hour == job_delete.hour,
                job.day == job_delete.day_of_month,
                job.month == job_delete.month,
                job.dow == job_delete.day_of_week
            ):
                cron.remove(job)
                cron.write()
                logger.info(f"Job deleted: {job_delete}")
                return
            
        logger.info(f"Job not found: {job_delete}")
            
    except Exception as e:
        logger.error(f"Error deleting job: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=api_port)