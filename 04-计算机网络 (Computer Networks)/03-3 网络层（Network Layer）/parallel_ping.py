#!/usr/bin/env python3
import threading
import time
import os
import statistics
from scapy.all import ICMP, IP, sr1, conf

# 读取 IP 地址列表 文件 ip.lst
def load_ip_list(filename="ip.lst"):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: 文件 {filename} 不存在！")
        exit(1)

ip_list = load_ip_list()

# 存储每个 IP 的统计数据
stats = {}
stats_lock = threading.Lock()

# 初始化统计数据
for ip in ip_list:
    stats[ip] = {
        'snt': 0,      # 已发送包数
        'loss': 0,     # 丢失包数
        'last': None,  # 最后一次延时（ms）
        'delays': []   # 所有成功的延时
    }

def icmp_ping(ip):
    """ 使用 ICMP Echo 请求 ping 目标 IP，并更新统计数据 """
    while True:
        with stats_lock:
            stats[ip]['snt'] += 1  # 记录发送包数

        # 发送 ICMP Echo 请求
        packet = IP(dst=ip) / ICMP()
        start_time = time.time()

        reply = sr1(packet, timeout=1, verbose=False)

        end_time = time.time()
        if reply:
            rtt = (end_time - start_time) * 1000  # 转换为毫秒
            with stats_lock:
                stats[ip]['last'] = rtt
                stats[ip]['delays'].append(rtt)
        else:
            with stats_lock:
                stats[ip]['loss'] += 1
                stats[ip]['last'] = None

        time.sleep(1)  # 控制间隔 1 秒

def compute_stats(delays):
    """计算统计数据"""
    if not delays:
        return None, None, None, None
    avg = sum(delays) / len(delays)
    best = min(delays)
    wrst = max(delays)
    stdev = statistics.stdev(delays) if len(delays) > 1 else 0.0
    return avg, best, wrst, stdev

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def display_stats():
    """实时显示统计结果"""
    while True:
        clear_screen()
        header = f"{'IP地址':15} {'Loss':>8} {'Snt':>6} {'Last':>8} {'Avg':>8} {'Best':>8} {'Wrst':>8} {'StDev':>8}"
        print(header)
        print("-" * len(header))

        with stats_lock:
            for ip in ip_list:
                snt = stats[ip]['snt']
                loss_count = stats[ip]['loss']
                loss_rate = (loss_count / snt * 100) if snt > 0 else 0
                last = stats[ip]['last']
                avg, best, wrst, stdev = compute_stats(stats[ip]['delays'])

                print(f"{ip:15} {loss_rate:7.2f}% {snt:6d} "
                      f"{(f'{last:.2f}' if last is not None else '-'):>8} "
                      f"{(f'{avg:.2f}' if avg is not None else '-'):>8} "
                      f"{(f'{best:.2f}' if best is not None else '-'):>8} "
                      f"{(f'{wrst:.2f}' if wrst is not None else '-'):>8} "
                      f"{(f'{stdev:.2f}' if stdev is not None else '-'):>8}")
        time.sleep(1)

# 启动 ICMP 线程
threads = []
for ip in ip_list:
    t = threading.Thread(target=icmp_ping, args=(ip,), daemon=True)
    t.start()
    threads.append(t)

# 运行显示统计的主线程
try:
    display_stats()
except KeyboardInterrupt:
    print("程序终止")
