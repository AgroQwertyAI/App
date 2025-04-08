from src.auxiliary import get_data, save_data_to_filesystem
from src.schemas import CronArgs
import sys

if __name__ == "__main__":
    import asyncio

    folder_name = sys.argv[1]
    format = sys.argv[2]
    chat_id = sys.argv[3]
    type = sys.argv[4]

    if type == "filesystem":
        cron_args = CronArgs(folder_name=folder_name, format=format, chat_id=chat_id, type=type)

        data = asyncio.run(get_data(cron_args))
        save_data_to_filesystem(cron_args=cron_args, data=data)

    elif type == "drive":
        raise NotImplementedError("Drive is not implemented yet")
