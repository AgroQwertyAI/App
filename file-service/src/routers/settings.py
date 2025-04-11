from fastapi import APIRouter, Query
from src.schemas.setting import SettingGet, SettingPost, SettingPatch

settings_router = APIRouter(tags=["settings"])


@settings_router.get(
    "/settings", 
    response_model=list[SettingGet], 
    description="Get all settings", 
)
async def get_settings(
    offset: int = Query(default=0, description="The offset of the settings"), 
    limit: int = Query(default=10, description="The limit of the settings"),
    show_deleted: bool = Query(default=False, description="Show deleted settings"),
    name_contains: str = Query(default="", description="The name of the setting to search for")
):
    pass


@settings_router.post(
    "/setting", 
    response_model=SettingGet, 
    description="Create a new setting", 
)
async def post_setting(
    setting: SettingPost
):
    pass


@settings_router.patch(
    "/setting/{id}", 
    response_model=SettingGet, 
    description="Update a setting by its id", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def update_setting(
    id: int, 
    setting_patch: SettingPatch
):
    pass


@settings_router.delete(
    "/setting/{id}", 
    response_model=None,
    description="Delete a setting by its id", 
    responses={404:{
        "description": "Setting not found"
    }}
)
async def delete_setting(
    id: int
):
    pass