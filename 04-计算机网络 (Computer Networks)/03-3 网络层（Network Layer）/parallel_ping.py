import os
import time
import struct
import random
import socket
import threading
import statistics
import queue

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0

'''
这个任务需要：
从文件读取 IP 列表
多线程/多进程并行发送 ICMP 请求
基于 ICMP 报文时间戳计算 RTT
主线程每秒清屏刷新一次结果

📌 实现方案
threading: 每个 IP 启动一个线程执行 ping
queue.Queue: 用于线程间通信，主线程每秒刷新结果
os.system("cls" / "clear"): 清屏
time.sleep(1): 定时刷新
'''

# 计算校验和
def checksum(source_string):
    sum = 0
    count_to = (len(source_string) // 2) * 2
    count = 0

    while count < count_to:
        this_val = source_string[count + 1] * 256 + source_string[count]
        sum = sum + this_val
        sum = sum & 0xFFFFFFFF
        count += 2

    if count_to < len(source_string):
        sum = sum + source_string[-1]
        sum = sum & 0xFFFFFFFF

    sum = (sum >> 16) + (sum & 0xFFFF)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 0xFFFF
    answer = answer >> 8 | (answer << 8 & 0xFF00)
    return answer

# 发送 ICMP Echo Request
def send_icmp_echo(sock, dest_addr, packet_id, seq_number):
    timestamp = time.time()  # 发送时间（秒，带小数）
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, packet_id, seq_number)
    payload = struct.pack("!d", timestamp)  # 8字节时间戳
    checksum_val = checksum(header + payload)
    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, checksum_val, packet_id, seq_number)
    packet = header + payload
    sock.sendto(packet, (dest_addr, 1))

# 接收 ICMP Echo Reply
def receive_icmp_reply(sock, packet_id, seq_number):
    try:
        while True:
            packet, addr = sock.recvfrom(1024)
            icmp_header = packet[20:28]
            type, code, checksum, p_id, seq = struct.unpack("!BBHHH", icmp_header)

            if type == ICMP_ECHO_REPLY and p_id == packet_id and seq == seq_number:
                recv_timestamp = struct.unpack("!d", packet[28:36])[0]  # 解析 8 字节时间戳
                return recv_timestamp
    except socket.timeout:
        return None

# 并行 Ping 线程
def ping_worker(ip, result_queue):
    stats = {
        "IP": ip,
        "Snt": 0,
        "Recv": 0,
        "Loss": 0.0,
        "Last": 0.0000,
        "Avg": 0.0000,
        "Best": float("inf"),
        "Wrst": 0.0000,
        "StDev": 0.0000,
        "RTTs": []
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.settimeout(1)

    while True:
        packet_id = random.randint(0, 65535)
        seq_number = stats["Snt"]

        send_icmp_echo(sock, ip, packet_id, seq_number)
        send_time = time.time()
        stats["Snt"] += 1

        recv_timestamp = receive_icmp_reply(sock, packet_id, seq_number)
        recv_time = time.time()

        if recv_timestamp:
            rtt = round((recv_time - recv_timestamp) * 1000, 4)
            stats["RTTs"].append(rtt)
            stats["Recv"] += 1
            stats["Last"] = rtt
            stats["Best"] = round(min(stats["Best"], rtt), 4)
            stats["Wrst"] = round(max(stats["Wrst"], rtt), 4)
            stats["Avg"] = round(sum(stats["RTTs"]) / len(stats["RTTs"]), 4)
            stats["StDev"] = round(statistics.stdev(stats["RTTs"]), 4) if len(stats["RTTs"]) > 1 else 0.0000
        else:
            stats["Loss"] = round(((stats["Snt"] - stats["Recv"]) / stats["Snt"]) * 100, 2)

        result_queue.put(stats.copy())
        time.sleep(1)

# 从文件加载 IP
def load_ips(filename="ip.lst"):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: {filename} 文件不存在！")
        exit(1)

# 清屏
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

# 主线程：定时刷新统计信息
def display_stats(result_queue, ip_list):
    stats_map = {ip: {} for ip in ip_list}

    while True:
        while not result_queue.empty():
            data = result_queue.get()
            stats_map[data["IP"]] = data

        clear_screen()
        
        # 表头
        header = f"{'IP地址':<18} {'Loss%':<8} {'Snt':<5} {'Last':<10} {'Avg':<10} {'Best':<10} {'Wrst':<10} {'StDev':<10}"
        print(header)
        print("=" * len(header))

        # 逐行打印数据
        for ip, stats in stats_map.items():
            if stats:
                print(f"{stats['IP']:<18} {stats['Loss']:<8.2f} {stats['Snt']:<5} {stats['Last']:<10.4f} {stats['Avg']:<10.4f} {stats['Best']:<10.4f} {stats['Wrst']:<10.4f} {stats['StDev']:<10.4f}")
            else:
                print(f"{ip:<18} -       -     -         -         -         -         -         -")

        time.sleep(1)

if __name__ == "__main__":
    ip_list = load_ips()
    result_queue = queue.Queue()

    for ip in ip_list:
        threading.Thread(target=ping_worker, args=(ip, result_queue), daemon=True).start()

    display_stats(result_queue, ip_list)
