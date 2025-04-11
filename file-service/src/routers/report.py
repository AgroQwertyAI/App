from fastapi import APIRouter, Query
from datetime import datetime
from src.schemas.report import ReportGet

report_router = APIRouter(tags=["reports"])


@report_router.get(
    "/setting/{setting_id}/reports", 
    response_model=list[ReportGet], 
    description="Get all reports from a setting", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def get_reports(
    setting_id: int,
    offset: int = Query(default=0, description="The offset of the reports"), 
    limit: int = Query(default=10, description="The limit of the reports"),
    from_date: datetime = Query(default=None, description="The start date of the reports"),
    to_date: datetime = Query(default=None, description="The end date of the reports")
):
    pass


# @report_router.get(
#     "/setting/{setting_id}/report/{report_id}",
#     response_model=ReportGet,
#     description="Get a report from a setting by its id",
#     responses={404:{
#         "description": "Setting or report not found"
#     }}
# )
# async def get_report(
#     setting_id: int,
#     report_id: int
# ):
#     pass
