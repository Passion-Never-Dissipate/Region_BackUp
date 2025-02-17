from mcdreforged.api.utils.serializer import Serializable


class rb_info(Serializable):
    time: str = ""
    backup_dimension: str = ""
    user: str = ""
    command: str = ""
    comment: str = ""
    version_created: str = "1.9.0"


class rb_config(Serializable):
    server_path: str = "./server"
    backup_path: str = "./rb_multi"
    static_backup_path: str = "./rb_static"
    overwrite_backup_folder: str = "overwrite"
    bukkit_mode: bool = False
    dimension_info: dict[str, dict] = {
        "0": {"dimension": "overworld",
              "world_name": "world",
              "region_folder": [
                  "poi",
                  "entities",
                  "region"
              ]
              },
        "-1": {"dimension": "the_nether",
               "world_name": "world",
               "region_folder": [
                   "DIM-1/poi",
                   "DIM-1/entities",
                   "DIM-1/region"
               ]
               },
        "1": {"dimension": "the_end",
              "world_name": "world",
              "region_folder": [
                  "DIM1/poi",
                  "DIM1/entities",
                  "DIM1/region"
              ]
              }
    }
    dimension_info_for_bukkit: dict[str, dict] = {
        "0": {"dimension": "overworld",
              "world_name": "world",
              "region_folder": [
                  "poi",
                  "entities",
                  "region"
              ]
              },
        "-1": {"dimension": "the_nether",
               "world_name": "world_nether",
               "region_folder": [
                   "DIM-1/poi",
                   "DIM-1/entities",
                   "DIM-1/region"
               ]
               },
        "1": {"dimension": "the_end",
              "world_name": "world_the_end",
              "region_folder": [
                  "DIM1/poi",
                  "DIM1/entities",
                  "DIM1/region"
              ]
              }
    }
    minimum_permission_level: dict[str, int] = {
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
    slot: int = 10
    static_slot: int = 50
    plugin_version: str = "1.9.0"
