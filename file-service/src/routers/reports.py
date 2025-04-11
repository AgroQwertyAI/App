from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from src.schemas.endpoints.report import ReportGet
from src.session import get_session
import json

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
    with get_session() as conn:
        cursor = conn.cursor()
        
        # Check if setting exists
        cursor.execute("SELECT setting_id FROM settings WHERE setting_id = ?", (setting_id,))
        setting = cursor.fetchone()
        if not setting:
            raise HTTPException(status_code=404, detail="Setting not found")
        
        # Build the base query
        query = "SELECT * FROM reports WHERE setting_id = ?"
        params = [setting_id]
        
        # Add date range filters if provided
        if from_date:
            query += " AND timedata >= ?"
            params.append(from_date.isoformat())
        
        if to_date:
            query += " AND timedata <= ?"
            params.append(to_date.isoformat())
        
        # Add pagination
        query += " ORDER BY timedata DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert SQLite rows to ReportGet objects
        result = []
        for row in rows:
            report = ReportGet(
                report_id=row['report_id'],
                setting_id=row['setting_id'],
                timedata=datetime.fromisoformat(row['timedata']),
                file=row['file'],
                extra=json.loads(row['extra']) if row['extra'] else {}
            )
            result.append(report)
            
        return result


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
