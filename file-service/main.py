from fastapi import FastAPI, Query, HTTPException, status
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
    cron_jobs = []
    try:
        cron = CronTab(user=True)
        for job in cron:
            try:
                arguments = job.command.split(" ")
                if len(arguments) < 7:
                    logger.warning(f"Skipping job with unexpected command format: {job.command}")
                    continue

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
            except IndexError as ie:
                logger.warning(f"Skipping job due to parsing error (IndexError): {job.command} - {ie}")
            except Exception as e_inner:
                logger.warning(f"Skipping job due to unexpected error: {job.command} - {e_inner}")

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
        schedule_str = get_schedule(job)
        cron = CronTab(user=True)

        for existing_job in cron:
            if (existing_job.command == command and
                str(existing_job.minute) == str(job.minute) and
                str(existing_job.hour) == str(job.hour) and
                str(existing_job.day) == str(job.day_of_month) and
                str(existing_job.month) == str(job.month) and
                str(existing_job.dow) == str(job.day_of_week)):
                logger.warning(f"Job already exists: {job}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Identical cron job already exists."
                )

        new_job = cron.new(command=command)
        new_job.setall(schedule_str)

        cron.write()

        logger.info(f"Job created: {new_job}")
        return {"message": "Job created successfully", "job_details": str(new_job)}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise

@app.delete("/api/job")
async def delete_job(job_delete: CronJob = Query(...)):
    logger.info(f"Deleting job: {job_delete}")
    try:
        job_command_to_delete = get_command(job_delete)
        cron = CronTab(user=True)
        job_found_and_deleted = False
        for job in cron:
            if (
                job.command == job_command_to_delete and
                str(job.minute) == str(job_delete.minute) and
                str(job.hour) == str(job_delete.hour) and
                str(job.day) == str(job_delete.day_of_month) and
                str(job.month) == str(job_delete.month) and
                str(job.dow) == str(job_delete.day_of_week)
            ):
                cron.remove(job)
                cron.write()
                logger.info(f"Job deleted: {job_delete}")
                job_found_and_deleted = True

        if not job_found_and_deleted:
            logger.info(f"Job not found: {job_delete}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    except Exception as e:
        logger.error(f"Error deleting job: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(api_port))