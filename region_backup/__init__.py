import codecs
import datetime
import json
import os
import re
import shutil
import time
import math

from concurrent.futures import ThreadPoolExecutor
from mcdreforged.api.all import *
from region_backup.config import rb_info, rb_config
from region_backup.json_message import Message

Prefix = '!!rb'
# 默认的插件配置文件
cfg = rb_config
# 地狱，末地世界区域文件位置
dim_dict = {"the_nether": "DIM-1", "the_end": "DIM1"}
# 维度对应表
dim_list = {0: "overworld", 1: "the_end", -1: "the_nether"}
# 单维度完整备份列表
dim_folder = ["data", "poi", "entities", "region"]
# 全局分享列表
data_list = []
# 用户
user = None
# 备份状态符
backup_state = None
# 槽位默认数量
slot = 5
# 回档状态符
back_state = None
# 回档槽位
back_slot = None
# 超时
time_out = 5
# 本次备份是否为永久备份
static = None
# 静态备份指令运行状态


def print_help_msg(source: InfoCommandSource):
    if len(source.get_info().content.split()) < 2:
        source.reply(Message.get_json_str(tr("help_message", Prefix, "Region BackUp", "1.8.0")))
        source.get_server().execute_command("!!rb list", source)

    else:
        source.reply(Message.get_json_str(tr("full_help_message", Prefix)))


@new_thread("rb_make")
def rb_make(source: InfoCommandSource, dic: dict):
    global backup_state, user, static

    try:
        if not source.get_info().is_player:
            source.reply(tr("backup_error.source_error"))
            return

        if backup_state is None:
            backup_state = False

            if "cmt" not in dic:
                dic["cmt"] = tr("default_comment")

            r = int(dic["r"])

            if r < 0:
                source.reply(tr("backup_error.radius_error"))
                backup_state = None
                return

            source.get_server().broadcast(tr("backup.start"))

            get_user_info(source)

            t = time.time()
            while len(data_list) < 4:
                if time.time() - t > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            data = data_list.copy()
            data_list.clear()
            backup_pos = get_backup_pos(r, int(data[2][0] // 16), int(data[2][2] // 16))
            data[0] = source.get_info().player
            data[1] = source.get_info().content

            # 保存游戏
            source.get_server().execute("save-off")
            t1 = time.time()
            while backup_state != 1:
                if time.time() - t1 > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            source.get_server().execute("save-all flush")
            t1 = time.time()
            while backup_state != 2:
                if time.time() - t1 > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            user = None
            valid_pos = search_valid_pos(data[-1], backup_pos)
            is_static(data[1])

            rename_slot()

            copy_files(valid_pos, data[-1])

            make_info_file(dic["cmt"], data=data)

            t2 = time.time()
            source.get_server().broadcast(tr("backup.done", f"{(t2 - t):.2f}"))
            source.get_server().broadcast(
                tr("backup.date", f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"{dic['cmt']}")
            )

            source.get_server().execute("save-on")
            static = None
            backup_state = None
            return

    except Exception as e:
        user = None
        static = None
        backup_state = None
        source.reply(tr("backup_error.unknown_error", e))
        source.get_server().execute("save-on")
        return

    source.reply(tr("backup_error.repeat_backup"))


@new_thread("rb_pos_make")
def rb_pos_make(source: InfoCommandSource, dic: dict):
    global backup_state, user, static
    try:

        if backup_state is None:
            backup_state = False
            x1, z1, x2, z2 = dic["x1"], dic["z1"], dic["x2"], dic["z2"]

            if "cmt" not in dic:
                dic["cmt"] = tr("default_comment")

            dim = int(dic["dim"])

            if dim not in dim_list:
                backup_state = None
                source.reply(tr("backup_error.dim_error"))
                return

            dim = dim_list[dim]

            source.get_server().broadcast(tr("backup.start"))

            backup_pos = get_backup_pos(pos_list=[(int(x1 // 512), int(x2 // 512)), (int(z1 // 512), int(z2 // 512))])
            user = source.get_info().is_user
            # 保存游戏
            source.get_server().execute("save-off")
            t = time.time()
            while backup_state != 1:
                if time.time() - t > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            source.get_server().execute("save-all flush")
            t1 = time.time()
            while backup_state != 2:
                if time.time() - t1 > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            user = None
            valid_pos = search_valid_pos(dim, backup_pos)

            if all(not v for v in valid_pos.values()):
                backup_state = None
                source.reply(tr("backup_error.invalid_pos"))
                source.get_server().execute("save-on")
                return

            is_static(source.get_info().content)

            rename_slot()

            copy_files(valid_pos, dim)

            make_info_file(dic["cmt"], backup_dim=dim,
                           user_=source.get_info().player if source.get_info().player else tr("list.console"),
                           cmd=source.get_info().content
                           )

            t2 = time.time()
            source.get_server().broadcast(tr("backup.done", f"{(t2 - t):.2f}"))
            source.get_server().broadcast(
                tr("backup.date", f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"{dic['cmt']}"))

            source.get_server().execute("save-on")
            static = None
            backup_state = None
            return

    except Exception as e:
        static = None
        backup_state = None
        user = None
        source.reply(tr("backup_error.unknown_error", e))
        source.get_server().execute("save-on")
        return

    source.reply(tr("backup_error.repeat_backup"))


@new_thread("rb_dim_make")
def rb_dim_make(source: InfoCommandSource, dic: dict):
    global backup_state, user, static

    try:
        if backup_state is None:
            backup_state = False

            if "cmt" not in dic:
                dic["cmt"] = tr("default_comment")

            dim = dic["dim"]

            res = re.findall(r'-\d+|\d+', dim)
            dim = [int(s) if s[0] != '-' else -int(s[1:]) for s in res]
            if len(dim) != len(set(dim)):
                backup_state = None
                source.reply(tr("backup_error.dim_repeat"))
                return

            backup_list = []

            for i in dim:
                if i not in dim_list:
                    backup_state = None
                    source.reply(tr("backup_error.dim_error"))
                    return
                backup_list.append(dim_list[i])

            source.get_server().broadcast(tr("backup.start"))

            user = source.get_info().is_user
            # 保存游戏
            source.get_server().execute("save-off")
            t = time.time()
            while backup_state != 1:
                if time.time() - t > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            source.get_server().execute("save-all flush")
            t1 = time.time()
            while backup_state != 2:
                if time.time() - t1 > time_out:
                    source.get_server().broadcast(tr("backup_error.timeout"))
                    source.get_server().execute("save-on")
                    backup_state = None
                    user = None
                    return
                time.sleep(0.01)

            user = None

            is_static(source.get_info().content)

            rename_slot()

            dim_path = []

            for i in backup_list:
                if i in dim_dict:
                    dim_path.append(dim_dict[i])
                else:
                    for j in dim_folder:
                        dim_path.append(j)

            time.sleep(0.1)

            path_ = cfg.static_backup_path if static else cfg.backup_path

            for i in dim_path:
                shutil.copytree(os.path.join(cfg.world_path, i), os.path.join(path_, "slot1", i))

            make_info_file(dic["cmt"], backup_dim=",".join(backup_list),
                           user_=source.get_info().player if source.get_info().player else tr("console"),
                           cmd=source.get_info().content)

            t2 = time.time()
            source.get_server().broadcast(tr("backup.done", f"{(t2 - t):.2f}"))
            source.get_server().broadcast(
                tr("backup.date", f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"{dic['cmt']}"))

            source.get_server().execute("save-on")
            static = None
            backup_state = None
            return

    except Exception as e:
        user = None
        static = None
        backup_state = None
        source.reply(tr("backup_error.unknown_error", e))
        source.get_server().execute("save-on")
        return

    source.reply(tr("backup_error.repeat_backup"))


# 玩家信息类型有如下两种 坐标，即Pos 维度，即Dimension
@new_thread("user_info")
def get_user_info(source):
    global user, data_list

    user = source.get_info().player

    if user:

        source.get_server().execute(f"data get entity {user} Pos")
        source.get_server().execute(f"data get entity {user} Dimension")

        t1 = time.time()
        while len(data_list) < 2:
            if time.time() - t1 > time_out:
                return
            time.sleep(0.01)

        data_list.append([float(pos.strip('d')) for pos in data_list[0].strip("[]").split(',')])
        data_list.append(data_list[1].replace("minecraft:", "").strip('"'))


@new_thread("rb_back")
def rb_back(source: InfoCommandSource, dic: dict):
    global back_state, back_slot
    # 判断槽位非空

    if not dic:
        if source.get_info().content.split()[1] == "restore":
            dic["slot"] = "overwrite"
        else:
            dic["slot"] = 1
    cmd = source.get_info().content.split()
    path_ = cfg.static_backup_path if len(cmd) > 2 and cmd[2] == "-s" else cfg.backup_path
    path = path_ + f"/slot{dic['slot']}" if isinstance(dic["slot"], int) else os.path.join(cfg.backup_path, dic["slot"])

    if not os.path.exists(os.path.join(path, "info.json")):
        source.reply(tr("back_error.lack_info"))
        return

    if not get_total_size_of_folders(
            [os.path.join(path, f) for f in os.listdir(path) if
             os.path.isdir(os.path.join(path, f))])[-1]:
        source.reply(tr("back_error.lack_region"))
        return

    try:

        if back_state is None:

            back_state = 0
            # 等待确认
            with codecs.open(os.path.join(path, "info.json"), encoding="utf-8") as fp:
                info = json.load(fp)
                t = info["time"]
                cmt = info["comment"]

            source.reply(
                Message.get_json_str("\n".join([tr("back.start", dic["slot"], t, cmt), tr("back.click")]))
            )

            t1 = time.time()
            while not back_state:
                if time.time() - t1 > 10:
                    source.reply(tr("back_error.timeout"))
                    back_state = None
                    return
                time.sleep(0.01)

            if back_state is True:
                source.reply(tr("back.abort"))
                back_state = None
                return
            # 提示

            source.get_server().broadcast(tr("back.countdown"))

            for stop_time in range(1, 10):
                time.sleep(1)
                if back_state is True:
                    back_state = None
                    source.reply(tr("back.abort"))
                    return
                source.get_server().broadcast(Message.get_json_str(tr("back.count", f"{10 - stop_time}", dic["slot"])))

            back_slot = dic["slot"]
            # 停止服务器
            is_static(source.get_info().content)
            source.get_server().stop()
            back_state = None
            return

    except Exception as e:
        back_state = back_slot = None
        source.reply(tr("back_error.unknown_error", e))
        return

    source.reply(tr("back_error.repeat_back"))


def on_server_stop(server: PluginServerInterface, server_return_code: int):
    global back_slot, static

    try:
        if back_slot:
            if server_return_code != 0:
                back_slot = None
                server.logger.error(tr("back_error.server_error"))
                return

            server.logger.info(tr("back.run"))
            path_ = cfg.static_backup_path if static else cfg.backup_path

            if os.path.exists(f"{cfg.backup_path}/overwrite") and back_slot != "overwrite":
                shutil.rmtree(f"{cfg.backup_path}/overwrite")
                os.makedirs(f"{cfg.backup_path}/overwrite")

            path_ = path_ + f"/slot{back_slot}" if isinstance(back_slot, int) \
                else os.path.join(cfg.backup_path, "overwrite")

            with codecs.open(os.path.join(path_, "info.json"), encoding="utf-8") as fp:
                info = json.load(fp)
                dim = info["backup_dimension"]

            dim_path = []

            back_list = dim.split(",")

            for i in back_list:
                if i not in dim_list.values():
                    back_slot = None
                    server.logger.error(tr("back_error.wrong_dim"))
                    return

                if i in dim_dict:
                    dim_path.append(dim_dict[i])

                else:
                    for j in dim_folder:
                        dim_path.append(j)

            if info["command"].split()[1] == "dim_make":

                if back_slot != "overwrite":
                    for i in dim_path:
                        shutil.copytree(os.path.join(cfg.world_path, i), os.path.join(cfg.backup_path, "overwrite", i))
                        shutil.rmtree(os.path.join(cfg.world_path, i))
                        shutil.copytree(os.path.join(path_, i), os.path.join(cfg.world_path, i))
                    shutil.copy2(os.path.join(path_, "info.json"),
                                 os.path.join(cfg.backup_path, "overwrite", "info.json"))

                else:
                    for i in dim_path:
                        shutil.rmtree(os.path.join(cfg.world_path, i))
                        shutil.copytree(os.path.join(path_, i), os.path.join(cfg.world_path, i))

            else:

                lst = [i for i in os.listdir(os.path.join(path_)) if os.path.isdir(os.path.join(path_, i))]

                dim_name = dim_path[0] if dim_path[0] in dim_dict.values() else ""

                if back_slot != "overwrite":

                    for i in lst:
                        os.makedirs(f"{cfg.backup_path}/overwrite" + f"/{i}")

                    for backup_file in lst:
                        if get_total_size_of_folders([os.path.join(path_, backup_file)])[-1]:
                            lst_ = os.listdir(os.path.join(path_, backup_file))
                            for i in lst_:
                                # 复制即将被替换的区域到overwrite
                                shutil.copy2(os.path.join(cfg.world_path, dim_name, backup_file, i),
                                             os.path.join(cfg.backup_path, "overwrite", backup_file, i))
                                # 将备份的区域对存档里对应的区域替换
                                shutil.copy2(os.path.join(path_, backup_file, i),
                                             os.path.join(cfg.world_path, dim_name, backup_file, i))
                            # 复制本次回档槽位的info文件到overwrite
                            shutil.copy2(os.path.join(path_, "info.json"),
                                         os.path.join(cfg.backup_path, "overwrite", "info.json"))

                else:
                    for backup_file in lst:
                        if get_total_size_of_folders([os.path.join(path_, backup_file)])[-1]:
                            lst_ = os.listdir(os.path.join(path_, backup_file))
                            for i in lst_:
                                # 将备份的区域对存档里对应的区域替换
                                shutil.copy2(os.path.join(path_, backup_file, i),
                                             os.path.join(cfg.world_path, dim_name, backup_file, i))

            static = None
            back_slot = None

            server.start()

    except Exception as e:
        static = None
        back_slot = None
        server.logger.error(tr("back_error.unknown_error", e))
        return


def rb_del(source: InfoCommandSource, dic: dict):
    try:
        # 获取文件夹地址
        path = cfg.static_backup_path if source.get_info().content.split()[2] == "-s" else cfg.backup_path
        s = path + f"/slot{dic['slot']}"
        # 删除整个文件夹
        if os.path.exists(s):
            shutil.rmtree(s, ignore_errors=True)
            source.reply(tr("del", dic['slot']))
            return

        source.reply(tr("del_error.lack_slot", dic['slot']))

    except Exception as e:
        source.reply(tr("del_error.unknown_error", e))
        return


def rb_abort(source: CommandSource):
    global back_state
    # 当前操作备份信息
    if back_state is None:
        source.reply(tr("abort"))
        return
    back_state = True


def rb_confirm(source: CommandSource):
    global back_state
    if back_state is None:
        source.reply(tr("confirm"))
        return
    back_state = 1


def rename_slot(sort=None):
    path_ = cfg.static_backup_path if static else cfg.backup_path
    pattern = re.compile(r'^slot([1-9]\d*)$')

    # 获取所有符合条件的文件夹
    slot_list = [i for i in os.listdir(path_) if os.path.isdir(os.path.join(path_, i)) and pattern.match(i)]
    sorted_list = sorted(slot_list, key=lambda x: int(re.search(r'\d+', x).group()))
    temp = []

    def clear_temp():
        """清除临时文件夹的标记"""
        for i in temp:
            os.rename(os.path.join(path_, i), os.path.join(path_, i.strip("_temp")))

    def rename_slots(index=1):
        """重命名文件夹"""
        for i, v in zip(range(len(sorted_list) - 1, -1, -1), reversed(sorted_list)):
            new_name = f"slot{i + index}"
            if v == new_name:
                continue

            if i > 0 and new_name in sorted_list:
                temp.append(f"{new_name}_temp")
                os.rename(os.path.join(path_, v), os.path.join(path_, f"{new_name}_temp"))
            else:
                os.rename(os.path.join(path_, v), os.path.join(path_, new_name))

    if not sort:
        if static:
            if slot_list:
                rename_slots(2)
                clear_temp()
        else:
            if len(sorted_list) == cfg.slot:
                shutil.rmtree(os.path.join(path_, f"slot{cfg.slot}"), ignore_errors=True)
                sorted_list.pop()

            if slot_list:
                rename_slots(2)
                clear_temp()

        os.makedirs(os.path.join(path_, "slot1"), exist_ok=True)
        return

    if slot_list:
        rename_slots()
        clear_temp()

    return len([i for i in os.listdir(path_) if os.path.isdir(os.path.join(path_, i)) and pattern.match(i)])


def rb_list(source: InfoCommandSource, dic: dict):
    global static

    is_static(source.get_info().content)

    slot_ = rename_slot(1)

    if not slot_:
        static = None
        source.reply(tr("list.empty_slot"))
        return

    path_ = cfg.static_backup_path if static else cfg.backup_path

    p = 1 if not dic else dic["page"]

    page = math.ceil(slot_ / 10)

    if p > page:
        static = None
        source.reply(tr("list.out_page"))
        return

    msg_list = [tr("list.dynamic") if not static else tr("list.static")]
    start = 10 * (p - 1) + 1
    end = slot_ if 10 * (p - 1) + 1 <= slot_ <= 10 * p else 10 * p
    lp = p - 1 if p > 1 else 0
    np = p + 1 if p + 1 <= page else 0

    try:
        for i in range(start, end + 1):
            name = f"slot{i}"
            path = os.path.join(path_, name, "info.json")
            if os.path.exists(path):
                info = source.get_server().as_plugin_server_interface().load_config_simple(
                    path, in_data_folder=False, failure_policy="raise", echo_in_console=False
                )

                if info:
                    t = info["time"]
                    cmt = info["comment"]
                    dim = info['backup_dimension']
                    user_ = info["user"]
                    cmd = info["command"]
                    size = get_total_size_of_folders([os.path.join(path_, name)])
                    msg = tr("list.slot_info", i, size[0], t, cmt, "-s" if static else "", dim, user_, cmd)
                    msg_list.append(msg)
                    continue

                msg = tr("list.empty_size", i)
                msg_list.append(msg)

            else:
                msg = tr("list.empty_size", i)
                msg_list.append(msg)

        if lp:
            msg = tr("list.last_page", p, lp, "-s" if static else "")
            if np:
                msg = msg + "  " + tr("list.next_page", p, np, "-s" if static else "")
            msg = msg + "  " + tr("list.page", end, slot_)
            msg_list.append(msg)

        elif np:
            msg = tr("list.next_page", p, np, "-s" if static else "")
            msg = msg + "  " + tr("list.page", end, slot_)
            msg_list.append(msg)

        static = None
        source.reply(Message.get_json_str("\n".join(msg_list)))

        dynamic = get_total_size_of_folders([cfg.backup_path])[-1]

        static_ = get_total_size_of_folders([cfg.static_backup_path])[-1]

        msg = tr("list.total_size", convert_bytes(dynamic), convert_bytes(static_), convert_bytes(dynamic + static_))

        source.reply(msg)

    except Exception as e:
        static = None
        source.reply(tr("list_error", e))
        return


def get_folder_size(folder_path):
    """计算单个文件夹的大小"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                # 解析符号链接
                real_path = os.path.realpath(file_path)
                total_size += os.path.getsize(real_path)
            except (FileNotFoundError, PermissionError):
                # 忽略无法访问的文件
                continue

    return total_size


def get_total_size_of_folders(folder_paths):
    """计算多个文件夹的总大小（多线程优化）"""
    total_size = 0
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(get_folder_size, folder_path): folder_path for folder_path in folder_paths}
        for future in futures:
            try:
                total_size += future.result()
            except Exception as e:
                folder_path = futures[future]
                ServerInterface.get_instance().logger.info(f"计算 §c{folder_path} §r的大小时出错: §e{e}")

    return convert_bytes(total_size), total_size


def convert_bytes(size):
    """将字节数转换为人类可读的格式（如 KB、MB、GB）"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f}{unit}"
        size /= 1024

    return f"{size:.2f}PB"


def rb_reload(source: CommandSource):
    try:
        source.get_server().reload_plugin("region_backup")
        source.reply(tr("reload"))
    except Exception as e:
        source.reply(tr("reload_error", e))


def tr(key, *args):
    return ServerInterface.get_instance().tr(f"region_backup.{key}", *args)


def on_unload(server: PluginServerInterface):
    global user, back_state, backup_state, back_slot, static
    user = backup_state = back_state = back_slot = static = None


def is_static(cmd: str):
    global static
    if len(cmd.split()) > 2 and cmd.split()[2] == "-s":
        static = 1


def get_backup_pos(r=None, x=None, z=None, pos_list=None):
    backup_pos = []

    if not pos_list:
        return get_backup_pos(pos_list=[((x - r) // 32, (x + r) // 32), ((z + r) // 32, (z - r) // 32)])

    left = min(pos_list[0])
    right = max(pos_list[0])
    top = max(pos_list[-1])
    bottom = min(pos_list[-1])

    for x in range(left, right + 1):
        for z in range(bottom, top + 1):
            backup_pos.append((x, z))
    return backup_pos


def make_info_file(cmt, data=None, backup_dim=None, user_=None, cmd=None):
    path_ = cfg.static_backup_path if static else cfg.backup_path
    file_path = os.path.join(path_, "slot1", "info.json")

    info = rb_info.get_default().serialize()
    info["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info["backup_dimension"] = data[-1] if not backup_dim else backup_dim
    info["user_dimension"] = data[-1] if not backup_dim else tr("default_info")
    info["user"] = data[0] if not user_ else user_
    info["user_pos"] = ",".join(str(pos) for pos in data[2]) if not user_ else tr("default_info")
    info["command"] = data[1] if not cmd else cmd
    info["comment"] = cmt

    with codecs.open(file_path, "w", encoding="utf-8") as fp:
        json.dump(info, fp, ensure_ascii=False, indent=4)


def copy_files(valid_pos, data):
    time.sleep(0.1)

    path = os.path.join(cfg.world_path, dim_dict[data]) if data in dim_dict else cfg.world_path

    path_ = cfg.static_backup_path if static else cfg.backup_path
    for folder, positions in valid_pos.items():
        # 获取坐标的横纵坐标值
        if not positions:
            continue

        os.makedirs(os.path.join(path_, "slot1", f"{folder}"), exist_ok=True)
        for pos in positions:
            x, z = pos
            file_path = os.path.join(path, folder, f"r.{x}.{z}.mca")
            shutil.copy2(file_path, os.path.join(path_, "slot1", folder, f"r.{x}.{z}.mca"))


def search_valid_pos(data, backup_pos):
    valid_pos = {"region": [], "poi": [], "entities": []}

    if data in dim_dict:
        path = os.path.join(cfg.world_path, dim_dict[data])

    else:
        path = cfg.world_path

    for folder, positions in valid_pos.items():
        for pos in backup_pos:
            x, z = pos
            file = os.path.join(path, folder, f"r.{x}.{z}.mca")

            if os.path.exists(file):
                positions.append(pos)

    return valid_pos


def on_info(server: PluginServerInterface, info: Info):
    global backup_state
    if user:

        if info.content.startswith(f"{user} has the following entity data: ") and info.is_from_server:
            data_list.append(info.content.split(sep="entity data: ")[-1])
            return

        if info.content.startswith("Saved the game") and info.is_from_server:
            backup_state = 2
            return

        if info.content.startswith("Automatic saving is now disabled") and info.is_from_server:
            backup_state = 1
            return


def on_load(server: PluginServerInterface, old):
    global cfg

    if not os.path.exists(server.get_data_folder()):
        server.save_config_simple(rb_config.get_default(), in_data_folder=True)

    cfg = server.load_config_simple(in_data_folder=True, target_class=rb_config.get_default())

    os.makedirs(cfg.backup_path, exist_ok=True)

    os.makedirs(cfg.static_backup_path, exist_ok=True)

    for i in range(1, cfg.slot + 1):
        os.makedirs(cfg.backup_path + f"/slot{i}", exist_ok=True)

    level_dict = cfg.minimum_permission_level

    require = Requirements()

    server.register_help_message('!!rb', tr("register_message"))

    builder = SimpleCommandBuilder()

    builder.command("!!rb", print_help_msg)
    builder.command("!!rb help", print_help_msg)
    builder.command("!!rb make <r>", rb_make)
    builder.command("!!rb make <r> <cmt>", rb_make)
    builder.command("!!rb make -s <r>", rb_make)
    builder.command("!!rb make -s <r> <cmt>", rb_make)
    builder.command("!!rb dim_make <dim> <cmt>", rb_dim_make)
    builder.command("!!rb dim_make <dim>", rb_dim_make)
    builder.command("!!rb dim_make -s <dim>", rb_dim_make)
    builder.command("!!rb dim_make -s <dim> <cmt>", rb_dim_make)
    builder.command("!!rb pos_make <x1> <z1> <x2> <z2> <dim>", rb_pos_make)
    builder.command("!!rb pos_make <x1> <z1> <x2> <z2> <dim> <cmt>", rb_pos_make)
    builder.command("!!rb pos_make -s <x1> <z1> <x2> <z2> <dim>", rb_pos_make)
    builder.command("!!rb pos_make -s <x1> <z1> <x2> <z2> <dim> <cmt>", rb_pos_make)
    builder.command("!!rb back", rb_back)
    builder.command("!!rb back <slot>", rb_back)
    builder.command("!!rb back -s", rb_back)
    builder.command("!!rb back -s <slot>", rb_back)
    builder.command("!!rb restore", rb_back)
    builder.command("!!rb confirm", rb_confirm)
    builder.command("!!rb del <slot>", rb_del)
    builder.command("!!rb del -s <slot>", rb_del)
    builder.command("!!rb abort", rb_abort)
    builder.command("!!rb list", rb_list)
    builder.command("!!rb list <page>", rb_list)
    builder.command("!!rb list -s", rb_list)
    builder.command("!!rb list -s <page>", rb_list)
    builder.command("!!rb reload", rb_reload)

    builder.arg("x1", Number)
    builder.arg("z1", Number)
    builder.arg("x2", Number)
    builder.arg("z2", Number)
    builder.arg("dim", Text)
    builder.arg("r", Integer)
    builder.arg("cmt", GreedyText)
    builder.arg("slot", Integer)
    builder.arg("page", lambda page: Integer(page).at_min(1))

    for literal in rb_config.minimum_permission_level:
        permission = level_dict[literal]
        builder.literal(literal).requires(
            require.has_permission(permission),
            failure_message_getter=lambda err: tr("lack_permission")
        )

    builder.register(server)
