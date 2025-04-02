import json
import subprocess
import math
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
import os
# import heapq

# 全局变量
N = 10                  # EMA移动平均窗口大小
ALPHA = 2 / (N+1)       # EMA衰减因子
BETA = 2.0              # 权重平滑指数
W_MIN = 0.001           # 保底最小权重
BASE_LN = 0.8           # 响应时间惩罚指数
k_speed = 0.7           # 下载速度惩罚系数
# EPSILON = 0.2           # 随机抽样探索率

def debug_print(msg, data=None, prefix="[DEBUG] "):
    """统一的调试信息输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"{prefix}{timestamp} {msg}")
    if data is not None:
        print(f"{prefix}Data: {json.dumps(data, indent=2)}")

class GatewaySpeedTest:
    def __init__(self, main_gateway_file='ipfs_gateway.txt', 
                 side_gateway_file='ipfs_gateway_side.txt',
                 data_file='gateway_data.json',
                 log_dir='gateway_logs'):
        self.main_gateway_file = main_gateway_file
        self.side_gateway_file = side_gateway_file
        self.data_file = data_file
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.gateway_data = self.load_gateway_data()
        debug_print(f"已加载 {len(self.gateway_data['gateways'])} 个网关")

    def load_gateway_data(self):
        """从JSON文件加载网关数据，如果文件不存在则初始化新数据"""
        debug_print("开始加载网关数据")

        try:
            # 尝试加载现有数据
            if Path(self.data_file).exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    debug_print(f"从 {self.data_file} 加载了数据")
                    
                    # 更新所有网关条目的字段
                    updated_data = {'gateways': {}}
                    for url, gateway in data['gateways'].items():
                        updated_data['gateways'][url] = self.ensure_gateway_fields(gateway)
                    debug_print(f"更新了 {len(updated_data['gateways'])} 个网关的数据结构")
                    return updated_data
            else:
                debug_print("数据文件不存在，初始化新数据")
                return self._initialize_gateway_data()
                
        except Exception as e:
            debug_print(f"加载数据失败: {str(e)}", prefix="[ERROR] ")
            debug_print("初始化新数据", prefix="[RECOVERY] ")
            return self._initialize_gateway_data()

    def ensure_gateway_fields(self, gateway):
        """确保网关数据包含所有必需的字段"""
        # 创建一个新的默认条目
        default_entry = self._create_gateway_entry(
            url=gateway.get('url', ''),
            is_main=gateway.get('is_main', False)
        )
        
        # 保留现有数据中的值
        for key in default_entry.keys():
            if key in gateway and gateway[key] is not None:
                default_entry[key] = gateway[key]
                
        return default_entry

    def _initialize_gateway_data(self):
        """初始化网关数据结构"""
        debug_print("初始化新的网关数据结构")
        data = {'gateways': {}}
        
        # 读取并初始化主网关
        if Path(self.main_gateway_file).exists():
            with open(self.main_gateway_file, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        data['gateways'][url] = self._create_gateway_entry(url, is_main=True)
            debug_print(f"已初始化 {len(data['gateways'])} 个主网关")
        
        # 读取并初始化侧网关
        if Path(self.side_gateway_file).exists():
            with open(self.side_gateway_file, 'r') as f:
                count_before = len(data['gateways'])
                for line in f:
                    url = line.strip()
                    if url and url not in data['gateways']:
                        data['gateways'][url] = self._create_gateway_entry(url, is_main=False)
            debug_print(f"已初始化 {len(data['gateways']) - count_before} 个侧网关")
        
        return data

    def _create_gateway_entry(self, url, is_main=False):
        """创建新的网关条目"""
        return {
            'url': url,
            'is_main': is_main,
            'success_count': 0,              # 只统计206的成功次数
            'test_count': 0,                 # 只统计有效的测试次数（排除200状态码）
            'current_ema': 1.0,
            'current_weight': 1.0,
            'last_test_time': None,
            'last_response_time': None,
            'last_status_code': None,
            'last_download_speed': None,     # 最后一次下载速度 (KB/s)
            'avg_download_speed': 0,         # 平均下载速度
            'download_speeds_history': [],   # 历史下载速度记录
            # 历史数据相关字段
            'total_attempts': 0,             # 总尝试次数（包括所有状态码）
            'response_times_history': [],    # 存储最近N次响应时间
            'success_history': [],           # 存储最近N次成功状态
            'weight_history': [],            # 存储最近N次权重
            # 'bayesian_prior': 1.0,           # 贝叶斯先验
            # 'confidence': 1.0                # 置信度
        }

    def test_single_gateway(self, url):
        """测试单个网关的速度和状态"""
        debug_print(f"开始测试网关: {url}")
        if self.cid:
            test_file = self.cid
        else:
            test_file = "QmUNLLsPACCz1vLxQVkXqqLX5R1X345qqfHbsf67hvA3Nn" # 默认用空文件夹
            
        full_url = f"{url.rstrip('/')}/ipfs/{test_file}"
        debug_print(f"测试URL: {full_url}")
        
        # 准备 curl 命令
        cmd_curl = [
            'curl', '-L', 
            '-w', '%{http_code} %{time_starttransfer} %{speed_download} %{size_download}\n',
            '-o', 'NUL' if os.name == 'nt' else '/dev/null', 
            '-s', '--max-time', '15',
            '--range', '0-1048576',
            full_url
        ]
        debug_print(f"CURL命令: {' '.join(cmd_curl)}")

        # 为 Windows 平台设置 subprocess 标志
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            startupinfo = None
            creationflags = 0

        try:
            result = subprocess.run(
                cmd_curl, 
                capture_output=True, 
                text=True, 
                timeout=15,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            output = result.stdout.strip()
            debug_print(f"CURL输出: {output}")
            
            parts = output.split()
            if len(parts) == 4:
                http_code, time_starttransfer, speed_download, size_download = parts
                http_code = int(http_code)
                time_starttransfer = float(time_starttransfer)
                speed_download = float(speed_download)
                size_download = int(size_download)

                # 确保响应时间不超过1500ms
                response_time = min(time_starttransfer * 1000, 1500)

                # 计算等效下载速度
                effective_speed = size_download / time_starttransfer if time_starttransfer > 0 else 0

                if size_download == 0:
                    debug_print(f"下载大小为0: {url}")
                    return {
                        'response_time': 1500,
                        'status_code': http_code,
                        'speed': 0,
                        'size': 0
                    }

                test_result = {
                    'response_time': response_time,
                    'status_code': http_code,
                    'speed': effective_speed,
                    'size': size_download
                }
                debug_print(f"测试完成: {url}", test_result)
                return test_result
                
            else:
                debug_print(f"无效输出: {url}", {'output': output})
                return {
                    'response_time': 1500,
                    'status_code': 0,
                    'speed': 0,
                    'size': 0
                }
                
        except subprocess.TimeoutExpired:
            debug_print(f"测试超时: {url}")
            return {
                'response_time': 1500,
                'status_code': 0,
                'speed': 0,
                'size': 0
            }
        except Exception as e:
            debug_print(f"测试失败: {url}", {'error': str(e)}, prefix="[ERROR] ")
            return {
                'response_time': 1500,
                'status_code': 0,
                'speed': 0,
                'size': 0
            }

    def run_speed_test(self, cid=None, cids=None, idx=0, epoch=0, max_workers=50):
        """运行多线程速度测试（测试单个CID）"""
        debug_print(f"开始批量测速，最大并发数: {max_workers}")
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.test_single_gateway, url): url 
                for url in self.gateway_data['gateways']
            }
            
            debug_print(f"提交了 {len(future_to_url)} 个测试任务")
            completed = 0
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                completed += 1
                try:
                    test_result = future.result()
                    self.update_gateway_stats(url, test_result)
                    results.append({
                        'url': url,
                        'result': test_result
                    })
                    debug_print(f"网关进度: {completed}/{len(future_to_url)} cid进度: {idx+1}/{len(cids)} epoch: {epoch+1} cid: {cid} 完成测试: {url}")
                except Exception as e:
                    debug_print(f"测试异常: {url} - {str(e)}", prefix="[ERROR] ")

        elapsed_time = time.time() - start_time
        debug_print(f"批量测速完成，耗时: {elapsed_time:.2f}秒")
        self.save_gateway_data()
        return results

    def test_cids(self, cids, epoch=0, max_workers=50):
        """测试多个CID的网关性能"""
        if not isinstance(cids, (list, tuple)):
            cids = [cids]
            
        debug_print(f"开始测试 {len(cids)} 个CID")
        
        for idx, cid in enumerate(cids):
            debug_print(f"\n开始测试CID: {cid}")
            self.cid = cid
            
            # 为每个CID创建单独的日志文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"gateway_test_{cid}_{timestamp}.log"
            
            # 运行测速
            results = self.run_speed_test(cid, cids, idx, epoch, max_workers)

            # 获取测速结果
            ranked_gateways = self.get_ranked_gateways()
            
            # 保存测试结果
            self.save_test_results_log(ranked_gateways, log_file)
            self.save_test_results_log(ranked_gateways) # 保存一个最新的到根目录
            
            # 打印当前CID的测试结果
            self._print_test_results(ranked_gateways, cid)
            
        # 生成汇总报告
        summary_file = self.log_dir / f"summary_report_{timestamp}.log"
        self._generate_summary_report(cids, summary_file)
        self._generate_summary_report(cids) # 保存一个最新的到根目录

    def _print_test_results(self, ranked_gateways, cid):
        """打印单个CID的测试结果"""
        print(f"\n{'='*50}")
        print(f"\nCID: {cid} 的测试结果：")
        
        col_widths = {
            'url': 50,
            'is_main': 8,
            'weight': 7,
            'ema': 7,
            'response_time': 10,
            'status_code': 8,
            'success_rate': 10,
            'test_count': 12,
            'speed': 12
        }
        
        header = (
            f"{'网关URL':<{col_widths['url']}} "
            f"{'主网关':<{col_widths['is_main']}} "
            f"{'权重':<{col_widths['weight']}} "
            f"{'EMA':<{col_widths['ema']}} "
            f"{'响应时间':<{col_widths['response_time']}} "
            f"{'状态码':<{col_widths['status_code']}} "
            f"{'成功率':<{col_widths['success_rate']}} "
            f"{'有效/总测试':<{col_widths['test_count']}} "
            f"{'下载速度':<{col_widths['speed']}}"
        )
        print(header)
        print("-" * (sum(col_widths.values()) + 10))
        
        for gateway in ranked_gateways:
            try:
                success_rate = f"{gateway.get('success_rate', 0):.2%}" if gateway.get('test_count', 0) > 0 else "N/A"
                is_main_mark = "是" if gateway.get('is_main', False) else "否"
                
                # 安全地获取下载速度
                speed = gateway.get('last_download_speed')
                speed_str = f"{speed:.1f} KB/s" if speed is not None else "N/A"
                
                row = (
                    f"{gateway.get('url', 'Unknown'):<{col_widths['url']}} "
                    f"{is_main_mark:<{col_widths['is_main']}} "
                    f"{gateway.get('weight', 0):<{col_widths['weight']}.3f} "
                    f"{gateway.get('ema', 0):<{col_widths['ema']}.3f} "
                    f"{gateway.get('last_response_time', 0):<{col_widths['response_time']}.1f} "
                    f"{gateway.get('last_status_code', 0):<{col_widths['status_code']}} "
                    f"{success_rate:<{col_widths['success_rate']}} "
                    f"{gateway.get('test_count', 0)}/{gateway.get('total_attempts', 0):<{col_widths['test_count']}} "
                    f"{speed_str}"
                )
                print(row)
            except Exception as e:
                debug_print(f"打印网关数据时出错: {gateway.get('url', 'Unknown')} - {str(e)}", prefix="[ERROR] ")

    def _generate_summary_report(self, cids, summary_file="summary_report_latest.log"):
        """生成测试汇总报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=== IPFS网关测试汇总报告 ===\n\n")
                f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"测试的CID数量: {len(cids)}\n\n")
                
                # 获取所有网关的排名
                ranked_gateways = self.get_ranked_gateways()
                
                f.write("\n=== 性能最佳的网关 (Top 20) ===\n")
                f.write("-" * 120 + "\n")
                f.write(f"{'网关URL':<49} {'权重':<6} {'成功率':<5} {'响应时间':<7} {'平均速度':<8} {'最大速度':<9} {'不稳定性':<8}\n")
                f.write("-" * 120 + "\n")
                
                for gw in ranked_gateways[:20]:
                    success_rate = f"{gw['success_rate']:.2%}" if gw['test_count'] > 0 else "N/A"
                    f.write(
                        f"{gw['url']:<50} "
                        f"{gw['weight']:<8.3f} "
                        f"{success_rate:<8} "
                        f"{gw['last_response_time']:<10.1f} "
                        f"{gw['avg_download_speed']:<12.1f} "
                        f"{gw['max_download_speed']:<12.1f} "
                        f"{gw['speed_stability']:<8.2f}\n"
                    )
                
                f.write("\n=== 各CID详细测试结果 ===\n")
                for cid in cids:
                    f.write(f"\nCID: {cid}\n")
                    f.write("-" * 50 + "\n")
                    
                    # 获取该CID最新的日志文件
                    log_files = list(self.log_dir.glob(f"gateway_test_{cid}_*.log"))
                    if log_files:
                        latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                        with open(latest_log, 'r', encoding='utf-8') as log:
                            stats_section = False
                            for line in log:
                                if line.strip() == "统计信息:":
                                    stats_section = True
                                elif stats_section and line.strip():
                                    f.write(line)
                
                f.write("\n\n=== 网关性能分析 ===\n")
                
                # 计算整体统计信息
                active_gateways = [gw for gw in ranked_gateways if gw['test_count'] > 0]
                total_gateways = len(ranked_gateways)
                active_count = len(active_gateways)
                
                f.write(f"\n总网关数量: {total_gateways}")
                f.write(f"\n活跃网关数量: {active_count}")
                
                if active_count > 0:
                    # 速度统计
                    avg_speeds = [gw['avg_download_speed'] for gw in active_gateways if gw['avg_download_speed'] > 0]
                    if avg_speeds:
                        f.write(f"\n平均下载速度: {sum(avg_speeds) / len(avg_speeds):.2f} KB/s")
                        f.write(f"\n最高下载速度: {max(gw['max_download_speed'] for gw in active_gateways):.2f} KB/s")
                    
                    # 响应时间统计
                    response_times = [gw['last_response_time'] for gw in active_gateways]
                    f.write(f"\n平均响应时间: {sum(response_times) / len(response_times):.2f} ms")
                    f.write(f"\n最快响应时间: {min(response_times):.2f} ms")
                    
                    # 成功率统计
                    success_rates = [gw['success_rate'] for gw in active_gateways]
                    avg_success_rate = sum(success_rates) / len(success_rates)
                    f.write(f"\n平均成功率: {avg_success_rate:.2%}")
                
                f.write("\n\n=== 速度分布统计 ===\n")
                speed_ranges = {
                    '极快 (>1000KB/s)': lambda s: s > 1000,
                    '快速 (500-1000KB/s)': lambda s: 500 <= s <= 1000,
                    '中等 (200-500KB/s)': lambda s: 200 <= s < 500,
                    '慢速 (50-200KB/s)': lambda s: 50 <= s < 200,
                    '极慢 (<50KB/s)': lambda s: s < 50
                }
                
                for range_name, range_func in speed_ranges.items():
                    count = sum(1 for gw in active_gateways if range_func(gw['avg_download_speed']))
                    if active_count > 0:
                        percentage = (count / active_count) * 100
                        f.write(f"\n{range_name}: {count} 个网关 ({percentage:.1f}%)")
                
            debug_print(f"汇总报告已保存到: {summary_file}")
        except Exception as e:
            debug_print(f"生成汇总报告失败: {str(e)}", prefix="[ERROR] ")

    def calculate_gamma_time(self, response_time):
        """计算响应时间惩罚参数 γ_time"""
        k = -math.log(BASE_LN)
        gamma_time = math.exp(-k * response_time / 1500)
        debug_print(f"计算gamma: response_time={response_time}, k={k}, gamma_time={gamma_time}")
        return gamma_time

    def calculate_gamma_speed(self, speed):
        """计算下载速度惩罚参数 γ_speed"""
        k = 1 / k_speed - 1
        gamma_speed = 1 / (1 + k * math.exp(-speed / 1024))
        debug_print(f"计算gamma: speed={speed}, k={k}, gamma_speed={gamma_speed}")
        return gamma_speed

    def update_gateway_stats(self, url, test_result):
        """更新网关统计信息"""
        try:
            # 1. 初始化和数据准备
            debug_print(f"更新网关统计: {url}")
            debug_print("测试结果:", test_result)
            
            gateway = self.gateway_data['gateways'][url]
            gateway = self.ensure_gateway_fields(gateway)
            self.gateway_data['gateways'][url] = gateway

            status_code = test_result['status_code']
            response_time = min(test_result['response_time'], 1500)  # 限制最大响应时间
            download_speed = test_result['speed'] / 1024  # 转换为 KB/s
            
            # 记录更新前状态
            old_stats = {
                'ema': gateway['current_ema'],
                'weight': gateway['current_weight'],
                'success_count': gateway['success_count'],
                'test_count': gateway['test_count'],
                'total_attempts': gateway['total_attempts'],
                'avg_download_speed': gateway['avg_download_speed']
            }
            debug_print("更新前状态:", old_stats)
            
            # 2. 更新基础统计信息
            gateway['total_attempts'] += 1
            gateway['last_test_time'] = datetime.now().isoformat()
            gateway['last_response_time'] = response_time
            gateway['last_status_code'] = status_code
            gateway['last_download_speed'] = download_speed
            
            # 3. 更新下载速度统计
            gateway['download_speeds_history'].append(download_speed)
            if len(gateway['download_speeds_history']) > 10:
                gateway['download_speeds_history'] = gateway['download_speeds_history'][-10:]
            
            # 计算有效下载速度的平均值（排除0值）
            valid_speeds = [s for s in gateway['download_speeds_history'] if s > 0]
            gateway['avg_download_speed'] = sum(valid_speeds) / len(valid_speeds) if valid_speeds else 0
            
            # 4. 更新测试计数和状态
            gateway['test_count'] += 1
            current_success = 1 if status_code == 206 else 0
            if current_success:
                gateway['success_count'] += 1

            #########################################################
            #########################算法部分#########################
            #########################################################    
            # 5. 计算新的权重
            ## 5.1 更新 EMA
            old_ema = gateway['current_ema']
            new_ema = ALPHA * current_success + (1 - ALPHA) * old_ema
            gateway['current_ema'] = new_ema
            
            ## 5.2 计算惩罚项
            ## 5.2.1 计算响应时间惩罚
            gamma_time = self.calculate_gamma_time(response_time)
            ## 5.2.2 计算下载速度惩罚
            gamma_speed = self.calculate_gamma_speed(download_speed)

            ## 5.3 计算最终权重
            base_weight = math.pow(new_ema, BETA)                                   # EMA加权
            final_weight = max(base_weight * gamma_time * gamma_speed, W_MIN)       # 应用惩罚项并确保最小权重
            gateway['current_weight'] = final_weight
            #########################################################
            

            # 更新权重历史
            gateway['weight_history'] = gateway.get('weight_history', [])[-9:] + [final_weight]
            
            # 6. 记录详细的更新结果
            debug_print("更新后状态:", {
                'ema': new_ema,
                'gamma_time': gamma_time,
                'gamma_speed': gamma_speed,
                'base_weight': base_weight,
                'final_weight': final_weight,
                'success_count': gateway['success_count'],
                'test_count': gateway['test_count'],
                'total_attempts': gateway['total_attempts'],
                'avg_download_speed': gateway['avg_download_speed']
            })
            
        except Exception as e:
            debug_print(f"更新网关统计时出错: {str(e)}", prefix="[ERROR] ")
            # 确保即使出错也不会丢失网关数据
            if url in self.gateway_data['gateways']:
                self.gateway_data['gateways'][url] = self._create_gateway_entry(
                    url, is_main=self.gateway_data['gateways'][url].get('is_main', False))

    def get_ranked_gateways(self):
        """获取按权重排序的网关列表"""
        ranked_gateways = [
            {
                'url': url,
                'weight': data['current_weight'],
                'ema': data['current_ema'],
                'is_main': data['is_main'],
                'last_response_time': data['last_response_time'],
                'last_status_code': data['last_status_code'],
                'success_count' : data['success_count'],
                'success_rate': (data['success_count'] / data['test_count'] 
                            if data['test_count'] > 0 else 0),
                'test_count': data['test_count'],
                'total_attempts': data['total_attempts'],
                # 添加下载速度相关字段
                'last_download_speed': data.get('last_download_speed', 0),
                'avg_download_speed': data.get('avg_download_speed', 0),
                'download_speeds_history': data.get('download_speeds_history', []),
                # 添加最大下载速度
                'max_download_speed': max(data.get('download_speeds_history', [0])) if data.get('download_speeds_history') else 0
            }
            for url, data in self.gateway_data['gateways'].items()
        ]
        
        # 使用 get 方法安全地访问字段，并提供默认值
        for gateway in ranked_gateways:
            # 计算近期平均下载速度（只考虑最近5次有效速度）
            recent_speeds = [s for s in gateway['download_speeds_history'][-5:] if s > 0]
            gateway['recent_avg_speed'] = (
                sum(recent_speeds) / len(recent_speeds) if recent_speeds else 0
            )
            
            # 计算下载速度的稳定性（标准差）
            if len(recent_speeds) > 1:
                mean = sum(recent_speeds) / len(recent_speeds)
                variance = sum((x - mean) ** 2 for x in recent_speeds) / len(recent_speeds)
                gateway['speed_stability'] = math.sqrt(variance)
            else:
                gateway['speed_stability'] = 0
        
        # 按权重降序排序
        ranked_gateways.sort(key=lambda x: x['weight'], reverse=True)
        
        # 添加调试信息
        debug_print("网关排名和速度信息:")
        for gw in ranked_gateways[:5]:  # 只显示前5个网关的信息
            debug_print(f"URL: {gw['url']}")
            debug_print(f"  最新速度: {gw['last_download_speed']:.2f} KB/s")
            debug_print(f"  平均速度: {gw['avg_download_speed']:.2f} KB/s")
            debug_print(f"  最大速度: {gw['max_download_speed']:.2f} KB/s")
            debug_print(f"  近期平均: {gw['recent_avg_speed']:.2f} KB/s")
            debug_print(f"  速度稳定性: {gw['speed_stability']:.2f}")
        
        return ranked_gateways

    def save_gateway_data(self):
        """保存网关数据到JSON文件"""
        try:
            # 保存前确保所有网关的数据结构都是完整的
            updated_data = {'gateways': {}}
            for url, gateway in self.gateway_data['gateways'].items():
                updated_data['gateways'][url] = self.ensure_gateway_fields(gateway)
                
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2)
            debug_print(f"已保存数据到 {self.data_file}")
        except Exception as e:
            debug_print(f"保存数据失败: {str(e)}", prefix="[ERROR] ")

    def save_test_results_log(self, ranked_gateways, log_file='gateway_test_results_latest.log'):
        """保存测试结果到日志文件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"\n\n=== 测试时间: {timestamp} ===\n\n")
                
                col_widths = {
                    'url': 46,
                    'is_main': 7,
                    'weight': 6,
                    'ema': 6,
                    'response_time': 6,
                    'status_code': 7,
                    'success_rate': 6,
                    'test_count': 9,
                    'speed': 6
                }
                
                header = (
                    f"{'网关URL':<{col_widths['url']}} "
                    f"{'主网关':<{col_widths['is_main']}} "
                    f"{'权重':<{col_widths['weight']}} "
                    f"{'EMA':<{col_widths['ema']}} "
                    f"{'响应时间':<{col_widths['response_time']}} "
                    f"{'状态码':<{col_widths['status_code']}} "
                    f"{'成功率':<{col_widths['success_rate']}} "
                    f"{'有效/总测试':<{col_widths['test_count']}} "
                    f"{'下载速度(单线程)'}"
                )
                f.write(header + '\n')
                f.write("-" * (sum(col_widths.values()) + 40) + '\n')
                
                for gateway in ranked_gateways:
                    try:
                        success_rate = f"{gateway.get('success_rate', 0):>6.2%}" if gateway.get('success_count', 0) > 0 else "   N/A"
                        is_main_mark = "是" if gateway.get('is_main', False) else "否"
                        
                        # 安全地获取下载速度
                        speed = gateway.get('last_download_speed')
                        speed_str = f"{speed:.1f} KB/s" if speed is not None else "N/A"
                        
                        row = (
                            f"{gateway.get('url', 'Unknown'):<50} "
                            f"{is_main_mark:<6} "
                            f"{gateway.get('weight', 0):<7.3f} "
                            f"{gateway.get('ema', 0):<7.3f} "
                            f"{gateway.get('last_response_time', 0):<10.1f} "
                            f"{gateway.get('last_status_code', 0):<5} "
                            f"{success_rate:>10} "
                            f"{gateway.get('success_count', 0):>8}/{gateway.get('total_attempts', 0):>} "
                            f"{speed_str:>15}"
                        )
                        f.write(row + '\n')
                    except Exception as e:
                        debug_print(f"写入网关数据时出错: {gateway.get('url', 'Unknown')} - {str(e)}", prefix="[ERROR] ")
                
                # 写入统计信息
                f.write("\n统计信息:\n")
                total_gateways = len(ranked_gateways)
                successful_gateways = sum(1 for g in ranked_gateways if g.get('success_rate', 0) > 0)
                
                # 安全计算平均值
                valid_times = [g.get('last_response_time', 0) for g in ranked_gateways if g.get('last_response_time')]
                avg_response_time = sum(valid_times) / len(valid_times) if valid_times else 0
                
                valid_speeds = [g.get('last_download_speed', 0) for g in ranked_gateways if g.get('last_download_speed')]
                avg_speed = sum(valid_speeds) / len(valid_speeds) if valid_speeds else 0
                
                f.write(f"总网关数: {total_gateways}\n")
                f.write(f"成功访问的网关数: {successful_gateways}\n")
                f.write(f"平均响应时间: {avg_response_time:.2f}ms\n")
                f.write(f"平均下载速度: {avg_speed:.2f}KB/s\n")
                
        except Exception as e:
            debug_print(f"保存日志文件失败: {str(e)}", prefix="[ERROR] ")










if __name__ == '__main__':
    debug_print("程序启动", prefix="[START] ")
    
    # 创建测速器实例
    tester = GatewaySpeedTest()
    
    # 运行测速
    print("\n" + "="*50)
    debug_print("开始网关测速...", prefix="[TEST] ")
    

    # 定义要测试的CID列表
    test_cids_lst = [
        # "bafybeibzwt25mk4vgasplipc5bevwhfccp54wnfw4derygtvx4d76qrdia",
        # "bafybeib2aporo44wnmvva6vxwdk3uua3amp3fumnw2hjxczniyptt6b7w4",
        # "bafybeidkwye2l6tkjxwd4mgr5duz444mcrjcjmoithb233lrzp4gwg5jsu",
        # "bafybeicosfzqogq4tqtlyvt4uktp7gc2phbvqpq3fnavchwlhbjbi74xtq",
        # "bafybeiegcfplaqji5qtm5zylvpqnvggh37rnsyewjjfo5d4husbfvphfmq",
        # "bafybeighbyqjzl2ajvp5ch3qb6leyvdgg4bsnfntkbzhwvndjapejeqkci",
        "bafybeic7s5lhpwl5vonetrhv5qjn5h7wplkjwupvou25yqm4peg6zvn3im",
        "bafybeidngm4u6rqg5stfbqp4d2v4zyakytp4elgya2kouufhhtrkwdrble",
        "bafybeidzmwwjp6jj5mrlubsgcglg3se7csved3j6rwezhfamplms6iwbvq",
        # 在此添加其他要测试的CID
    ]
    
    # 运行测试 (在 range 中调整要循环的轮数)
    for epoch in range(3):
        debug_print(f"第 {epoch+1} 轮网关测速...", prefix="[TEST] ")
        tester.test_cids(test_cids_lst, epoch)
        time.sleep(2)
        # results = tester.run_speed_test() # 测试空文件夹的 CID
    
    # 获取排名结果
    print("\n" + "="*50)
    ranked_gateways = tester.get_ranked_gateways()
    debug_print(f"获取到 {len(ranked_gateways)} 个网关的排名", prefix="[RANK] ")
 
    # 保存测试结果到日志文件
    tester.save_test_results_log(ranked_gateways)
    
    debug_print("程序结束", prefix="[END] ")