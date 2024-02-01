#                       _oo0oo_
#                      o8888888o
#                      88" . "88
#                      (| -_- |)
#                      0\  =  /0
#                    ___/`---'\___
#                  .' \\|     |// '.
#                 / \\|||  :  |||// \
#                / _||||| -:- |||||- \
#               |   | \\\  - /// |   |
#               | \_|  ''\---/''  |_/ |
#               \  .-\__  '-'  ___/-. /
#             ___'. .'  /--.--\  `. .'___
#          ."" '<  `.___\_<|>_/___.' >' "".
#         | | :  `- \`.;`\ _ /`;.`/ - ` : | |
#         \  \ `_.   \_ __\ /__ _/   .-` /  /
#     =====`-.____`.___ \_____/___.-`___.-'=====
#                       `=---='
#
#
#     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#           佛祖保佑       永不宕机     永无BUG
#
#       佛曰:
#               写字楼里写字间，写字间里程序员；
#               程序人员写程序，又拿程序换酒钱。
#               酒醒只在网上坐，酒醉还来网下眠；
#               酒醉酒醒日复日，网上网下年复年。
#               但愿老死电脑间，不愿鞠躬老板前；
#               奔驰宝马贵者趣，公交自行程序员。
#               别人笑我忒疯癫，我笑自己命太贱；
#               不见满街漂亮妹，哪个归得程序员？
#
#----------------------------------------------------------------
import os
import time
import zipfile
import shutil
import datetime
import codecs
import json

from mcdreforged.api.all import *

from region_backup.json_message import Message
from region_backup.edit_json import Edit_Read as edit
from region_backup.config import rb_info

Prefix = '!!rb'
# 备份总文件夹
backup_home = "./rb_multi"
# 备份文件夹位置
backup_path = "./rb_multi/slot{0}"
# 服务端存档位置
world_path = f"./server/world"
dim_dict = {"the_nether": "DIM-1", "the_end": "DIM1"}
data_list = []
user = None
backup_state = None
slot = 5
# 停止操作符
back_state = None
# 回档槽位
back_slot = None

help_msg = '''
------ {1} {2} ------
一个以区域为单位的§a备份回档§a插件
§3作者：FRUITS_CANDY
§d【格式说明】
#sc=!!rb<>st=点击运行指令#§7{0} §a§l[▷] §e显示帮助信息
#sc=!!rb make<>st=点击运行指令#§7{0} make §b<备份半径> <注释> §a§l[▷] §e以玩家为中心，备份边长为2倍半径+1的矩形区域
#sc=!!rb pos_make<>st=点击运行指令#§7{0} pos_make §b<x1坐标> <z1坐标> <x2坐标> <z2坐标> <维度> <注释> §a§l[▷] §e给定两个坐标点，备份以两坐标点对应的区域坐标为顶点形成的矩形区域
#sc=!!rb back<>st=点击运行指令#§7{0} back §b<槽位> §a§l[▷] §e回档指定槽位所对应的区域
#sc=!!rb del<>st=点击运行指令#§7{0} del §b<槽位> §a§l[▷] §e删除某槽位
#sc=!!rb confirm<>st=点击运行指令#§7{0} confirm §a§l[▷] §e再次确认是否回档
#sc=!!rb abort<>st=点击运行指令#§7{0} abort §a§l[▷] §e在任何时候键入此指令可中断回档
#sc=!!rb list<>st=点击运行指令#§7{0} list §a§l[▷] §e显示各槽位的存档信息
#sc=!!rb reload<>st=点击运行指令#§7{0} reload §a§l[▷] §e重载插件
'''.format(Prefix, "Region BackUp", "1.0.0")


def print_help_msg(source: CommandSource):
    source.reply(Message.get_json_str(help_msg))


@new_thread("rb_make")
def rb_make(source: InfoCommandSource, dic: dict):
    global backup_state
    if backup_state is None:
        text = dic["r_des"]
        lst = text.split()

        if len(lst) == 1:
            try:
                r = int(lst[0])
                des = "空"

            except ValueError:
                source.reply("输入错误")
                return
        else:
            try:
                r = int(lst[0])
                des = text.split(maxsplit=1)[1]

            except ValueError:
                source.reply("输入错误")
                return

        get_user_info(source)
        while len(data_list) < 4:
            time.sleep(0.01)

        data = data_list.copy()
        data_list.clear()
        backup_pos = get_backup_pos(r, int(data[2][0] // 512), int(data[2][2] // 512))
        data[0] = source.get_info().player
        data[1] = source.get_info().content

        # 保存游戏
        source.get_server().execute("save-all")
        while backup_state == 1:
            time.sleep(0.01)
        backup_state = None

        source.get_server().execute("save-off")
        while backup_state == 2:
            time.sleep(0.01)

        valid_pos = search_valid_pos(data, backup_pos)
        check_folder()

        rename_slot()

        make_info_file(data)

        compress_files(valid_pos, data)

        source.get_server().execute("save-on")
        backup_state = None


# 玩家信息类型有如下两种 坐标，即Pos 维度，即Dimension
@new_thread("user_info")
def get_user_info(source):
    global user, data_list
    user = source.get_info().player

    if user:

        source.get_server().execute(f"data get entity {user} Pos")
        source.get_server().execute(f"data get entity {user} Dimension")

        while len(data_list) < 2:
            time.sleep(0.01)

        data_list.append([float(pos.strip('d')) for pos in data_list[0].strip("[]").split(',')])
        data_list.append(data_list[1].strip('"minecraft:"'))
        user = None


def rb_position_make():
    pass


@new_thread("rb_back")
def rb_back(source: CommandSource, dic: dict):
    global back_state, back_slot
    # 判断槽位非空
    if not os.path.exists(os.path.join(backup_path.format(dic["slot"]), "info.json")):
        source.reply(f"该槽位为空不可回档")
        return

    # 等待确认
    source.reply("是否进行回档操作")
    while back_state is None:
        time.sleep(0.01)

    if back_state:
        back_state = None
        return
    # 提示
    source.reply("服务器将于10秒后关闭回档")
    for stop_time in range(1, 10):
        time.sleep(1)
        if back_state:
            back_state = None
            source.reply("回档已停止")
            return
        source.reply(f"还有{10 - stop_time}秒关闭,输入!!rb abort停止")
    back_state = None
    back_slot = dic["slot"]
    # 停止服务器
    source.get_server().stop()


'''
缺少对overwrite的info.json编写
'''


def on_server_stop(server: PluginServerInterface, server_return_code: int):
    global back_slot
    temp_slot = f"{backup_home}/overwrite"
    if back_slot:
        server.logger.error(f"正在运行文件替换")
        if os.path.exists(temp_slot):
            shutil.rmtree(f"{temp_slot}")
        os.makedirs(temp_slot)
        # 打开压缩文件

        for backup_file in ["entities.zip", "region.zip", "poi.zip"]:
            with zipfile.ZipFile(f"{backup_path.format(back_slot)}/{backup_file}") as zf:

                for over in zf.namelist():
                    with zipfile.ZipFile(f"{temp_slot}/{backup_file}", 'w') as zipf:
                        zipf.write(f"{world_path}/{backup_file.rstrip('zip')[:-1]}/{over}")

                zf.extractall(f"{world_path}/{backup_file.rstrip('zip')[:-1]}")

        back_slot = None

        server.start()


def rb_del(source: CommandSource, dic: dict):
    # 获取文件夹地址
    slot = backup_path.format(dic['slot'])
    if bool(os.listdir(f"{slot}")):
        # 删除整个文件夹
        shutil.rmtree(slot)
        # 创建文件夹
        os.makedirs(slot)
        source.reply(f"§4§l槽位{dic['slot']}删除成功")
        return
    # 判断槽位是否存在
    source.reply(f"§4§l槽位{dic['slot']}不存在")


@new_thread("rb_abort")
def rb_abort():
    global back_state, operate_source
    # 当前操作备份信息
    # 是否来自本插件调用
    operate_source = False
    back_state = True


@new_thread("rb_confirm")
def rb_confirm():
    global back_state
    back_state = False


def rb_list(source: CommandSource):
    """
    json文件格式
    展示颜色
    """
    backup_list = [backup_dir for backup_dir in os.listdir(backup_home) if not backup_dir.isalpha()]
    # 初始化消息
    msg_list = ["[备份列表]"]
    # 共计5个槽位
    for script in backup_list:
        try:
            # 尝试打开每个存档中的信息json文件
            with codecs.open(f"{backup_path.format(script[-1])}/info.json", "r", encoding="utf-8-sig") as backup_info:
                # 获取存档信息
                backup_show_info = json.load(backup_info)
                msg = f'[槽位{script[-1]}] 备份时间:{backup_show_info["time"]} 备份注释:{backup_show_info["comment"]}'
        except:
            # 读取不到的输出
            msg = f"[槽位{script[-1]}] 空"
        msg_list.append(msg)

    # 输出
    show_msg = "\n".join(msg_list)
    source.reply(show_msg)


def rb_reload(source: CommandSource):
    try:
        source.get_server().reload_plugin("region_backup")
        source.reply("§a§l插件已重载")
    except Exception as e:
        source.reply(f"§c§l重载插件失败: {e}")


def get_chunk_pos(pos):
    return pos // 16


def get_region_pos(pos):
    return pos // 512


def get_backup_pos(r, x, z):
    backup_pos = []
    n = (2 * r + 1) // 2

    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            backup_pos.append((x + i, z + j))

    return backup_pos


def check_folder(folder_path=None):
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)

    os.makedirs(backup_home, exist_ok=True)

    for i in range(1, slot + 1):
        os.makedirs(backup_path.format(i), exist_ok=True)


def make_info_file(data):
    file_path = os.path.join(backup_path.format(1), "info.json")

    info = rb_info.get_default().serialize()
    info["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info["backup_dimension"] = data[-1]
    info["user_dimension"] = data[-1]
    info["user"] = data[0]
    info["user_pos"] = ",".join(str(pos) for pos in data[2])
    info["command"] = data[1]
    info["comment"] = data[1].split(maxsplit=3)[-1]

    with codecs.open(file_path, "w", encoding="utf-8-sig") as fp:
        json.dump(info, fp, ensure_ascii=False, indent=4)


def rename_slot():
    move_dir()
    shutil.rmtree(backup_path.format(slot))
    if slot > 1:
        for i in range(slot - 1, 0, -1):
            os.rename(backup_path.format(i), backup_path.format(i + 1))

    os.makedirs(backup_path.format(1))


def compress_files(valid_pos, data):
    if data[-1] in dim_dict:
        path = os.path.join(world_path, dim_dict[data[-1]])

    else:
        path = world_path

    for folder, positions in valid_pos.items():
        # 获取坐标的横纵坐标值
        if not positions:
            continue

        with zipfile.ZipFile(os.path.join(backup_path.format(1), f"{folder}.zip"), 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pos in positions:
                x, z = pos

                file_path = os.path.join(path, folder, f"r.{x}.{z}.mca")

                zipf.write(file_path, arcname=f"r.{x}.{z}.mca")


def search_valid_pos(data, backup_pos):
    valid_pos = {"region": [], "poi": [], "entities": []}

    if data[-1] in dim_dict:
        path = os.path.join(world_path, dim_dict[data[-1]])

    else:
        path = world_path

    for folder, positions in valid_pos.items():
        for pos in backup_pos:
            x, z = pos
            file = os.path.join(path, folder, f"r.{x}.{z}.mca")

            if os.path.isfile(file):
                positions.append(pos)

    return valid_pos


def get_pos(info: Info, player):
    pass


def on_info(server: PluginServerInterface, info: Info):
    global backup_state
    if not user:
        return

    if info.content.startswith(f"{user} has the following entity data:") and info.is_from_server:
        data_list.append(info.content.split(sep="entity data: ")[-1])
        return

    if info.content.startswith("Saved the game") and info.is_from_server:
        backup_state = 1

    if info.content.startswith("Automatic saving is now disabled") and info.is_from_server:
        backup_state = 2


def move_dir():
    dic_dir = {}
    # 文件夹对应状态
    for item in [backup_dir for backup_dir in os.listdir(backup_home) if not backup_dir.isalpha()]:
        dic_dir[item] = bool(os.listdir(f"{backup_home}/{item}"))

    flag = []
    for file in dic_dir.keys():
        if dic_dir[file]:
            # 非空
            if bool(flag):
                os.rename(f"{backup_home}/{file}", f"{backup_home}/{flag[0]}")
                dic_dir[flag[0]] = True
                dic_dir[file] = False
                flag.append(file)
                flag.pop(0)
        else:
            # 空
            shutil.rmtree(f"{backup_home}/{file}")
            flag.append(file)

    for filename in flag:
        os.makedirs(f"{backup_home}/{filename}")


def on_load(server: PluginServerInterface, old):
    server.register_help_message('!!rb', '查看与区域备份有关的指令')

    builder = SimpleCommandBuilder()

    builder.command("!!rb", print_help_msg)
    builder.command("!!rb make <r_des>", rb_make)
    builder.command("!!rb pos_make <x1> <z1> <x2> <z2> <dim_des>", rb_position_make)
    builder.command("!!rb back <slot>", rb_back)
    builder.command("!!rb confirm", rb_confirm)
    builder.command("!!rb del <slot>", rb_del)
    builder.command("!!rb abort", rb_abort)
    builder.command("!!rb list", rb_list)
    builder.command("!!rb reload", rb_reload)

    builder.arg("r_des", GreedyText)
    builder.arg("x1", Number)
    builder.arg("z1", Number)
    builder.arg("x2", Number)
    builder.arg("z2", Number)
    builder.arg("dim_des", Integer)
    builder.arg("slot", Integer)

    builder.register(server)

    check_folder()

