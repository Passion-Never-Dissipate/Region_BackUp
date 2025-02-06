from mcdreforged.api.utils.serializer import Serializable
from typing import Dict


class rb_info(Serializable):
    time: str = ""
    backup_dimension: str = ""
    user_dimension: str = ""
    user: str = ""
    user_pos: float = ""
    command: str = ""
    comment: str = ""


class rb_config(Serializable):
    backup_path: str = "./rb_multi"
    static_backup_path: str = "./rb_static"
    world_path: str = "./server/world"
    minimum_permission_level: Dict[str, int] = {
        "make": 1,
        "pos_make": 1,
        "dim_make": 1,
        "back": 2,
        "restore": 2,
        "del": 2,
        "confirm": 1,
        "abort": 1,
        "reload": 2,
        "list": 0
    }
    slot: int = 5
    config_version: str = "1.8.0"

