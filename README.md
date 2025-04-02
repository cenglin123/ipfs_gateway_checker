# 程序设计

## 网关测速方法：

用法：将要测速的网关放入 `ipfs_gateway.txt` 或 `ipfs_gateway_side.txt` 中（前者叫主网关，后者叫副网关）。

用记事本或者其他代码编辑器打开 `ipfs_test_gateway_multi_cid.py` 文件，在下图中所示的位置填入要测试的 CID 以及循环的总轮数。

![程序使用说明](https://github.com/user-attachments/assets/50d5040c-337b-4e5b-8665-2ef14afd24ec)


然后在命令行中使用：

```cmd
python ipfs_test_gateway_multi_cid.py
```
运行程序。

测试的结果会显示在 `gateway_test_results_latest.log` 及 `summary_report_latest.log` 文件中。

前者显示所有网关的各项情况，如下（部分截取）：

```
=== 测试时间: 2025-04-02 22:46:07 ===

网关URL                                          主网关     权重     EMA    响应时间   状态码     成功率    有效/总测试    下载速度(单线程)
-------------------------------------------------------------------------------------------------------------------------------------------
https://ipfs.develop.ultimate-champions.com        否      0.905   1.000   415.5      206      100.00%       10/10     2464.7 KB/s
https://gw.w3ipfs.com:7443                         是      0.861   1.000   550.8      206      100.00%       10/10     1859.1 KB/s
https://ipfs.wenft.space                           否      0.704   0.901   530.8      206       80.00%        8/10     1929.2 KB/s
https://snapshot.4everland.link                    是      0.700   0.919   653.9      206       90.00%        9/10     1566.0 KB/s
https://ipfs.ketl.xyz                              否      0.654   0.945   1064.3     206       90.00%        9/10      962.1 KB/s
https://ipfs.axiom.trading                         否      0.639   1.000   1500.0     206      100.00%       10/10      542.7 KB/s
https://ipfs.farcana.com                           否      0.620   1.000   1500.0     206      100.00%       10/10      399.4 KB/s
...
...
```

后者显示排名前 20 的网关，并显示整体测试报告，示例如下：

```
=== IPFS网关测试汇总报告 ===

测试时间: 2025-04-02 22:46:05
测试的CID数量: 3


=== 性能最佳的网关 (Top 20) ===
------------------------------------------------------------------------------------------------------------------------
网关URL                                             权重     成功率   响应时间    平均速度     最大速度      不稳定性    
------------------------------------------------------------------------------------------------------------------------
https://ipfs.develop.ultimate-champions.com        0.905    100.00%  415.5      888.9        2464.7       533.49  
https://gw.w3ipfs.com:7443                         0.861    100.00%  550.8      1513.3       3277.5       1083.56 
https://ipfs.wenft.space                           0.704    80.00%   530.8      765.2        1929.2       792.23  
https://snapshot.4everland.link                    0.700    90.00%   653.9      601.2        1681.9       592.99  
https://ipfs.ketl.xyz                              0.654    90.00%   1064.3     402.9        962.1        357.36  
https://ipfs.axiom.trading                         0.639    100.00%  1500.0     398.6        864.9        273.72  
https://ipfs.farcana.com                           0.620    100.00%  1500.0     310.2        609.2        209.57  
https://d39z2iu8gx3qxr.cloudfront.net              0.619    100.00%  1500.0     288.0        439.6        83.17   
https://node0.dreamlink.cloud                      0.614    90.00%   1500.0     323.5        683.6        190.77  
https://ipfs.crewshop.world                        0.592    90.00%   1500.0     276.6        536.0        175.45  
https://cf-ipfs-gateway.infra.goldsky.com          0.592    90.00%   1500.0     300.9        536.6        173.15  
https://gw.w3ipfs.net:7443                         0.589    80.00%   1211.6     1521.9       2517.0       549.79  
https://ipfs-meta.blotocol.net                     0.588    100.00%  1500.0     442.2        1413.2       493.97  
https://gateway.ipfs.io                            0.587    100.00%  1500.0     381.5        1143.0       409.28  
https://storage.mojitonft.market                   0.579    100.00%  1500.0     239.2        511.4        133.72  
https://anotheranotheranother.ctm-demo.com         0.569    90.00%   1500.0     283.3        538.7        189.46  
https://www.ipfs.swrs.net                          0.564    100.00%  1500.0     14.3         30.7         8.88    
https://ipfs.decentralized-content.com             0.556    90.00%   1500.0     275.4        788.6        235.17  
https://ogpotheads.4everland.link                  0.550    90.00%   1500.0     301.5        653.7        210.13  
https://ipfs.trivium.network                       0.544    90.00%   1500.0     227.5        502.0        144.33  

=== 各CID详细测试结果 ===

CID: bafybeic7s5lhpwl5vonetrhv5qjn5h7wplkjwupvou25yqm4peg6zvn3im
--------------------------------------------------
总网关数: 743
成功访问的网关数: 440
平均响应时间: 1485.51ms
平均下载速度: 266.54KB/s

CID: bafybeidngm4u6rqg5stfbqp4d2v4zyakytp4elgya2kouufhhtrkwdrble
--------------------------------------------------
总网关数: 743
成功访问的网关数: 447
平均响应时间: 1481.36ms
平均下载速度: 286.39KB/s

CID: bafybeidzmwwjp6jj5mrlubsgcglg3se7csved3j6rwezhfamplms6iwbvq
--------------------------------------------------
总网关数: 743
成功访问的网关数: 448
平均响应时间: 1482.87ms
平均下载速度: 278.91KB/s


=== 网关性能分析 ===

总网关数量: 743
活跃网关数量: 743
平均下载速度: 271.37 KB/s
最高下载速度: 5869.72 KB/s
平均响应时间: 1482.87 ms
最快响应时间: 278.12 ms
平均成功率: 27.28%

=== 速度分布统计 ===

极快 (>1000KB/s): 3 个网关 (0.4%)
快速 (500-1000KB/s): 39 个网关 (5.2%)
中等 (200-500KB/s): 295 个网关 (39.7%)
慢速 (50-200KB/s): 106 个网关 (14.3%)
极慢 (<50KB/s): 300 个网关 (40.4%)

```

## 程序功能说明

### 已实现

1. **加载和初始化网关**：
   - 从自选网关文件 `ipfs_gateway.txt` 和次选网关文件 `ipfs_gateway_side.txt` 加载网关列表，初始化相关数据结构。
2. **测速函数**：
   - 使用 `curl` 命令测试每个网关，并记录 HTTP 状态码和响应时间（超时1500ms），可轮询多个 CID。
   - 仅 `206` 状态码表示成功，其余所有情况都表示失败。（ `200` 有可能是占位页面）
   - 如果成功则记录成功次数，并以 EMA 来累积计算可用性分数，并由 EMA 计算同步计算可用性权重（算法见后）
3. **保存json文件**：
   -  在同路径保存 `gateway_data.json` 文件，记录测试的信息，下次测试时读取并更新内容。
### 待实现

1. **加权随机抽样**：
   - 根据权重 $w$ 进行随机抽样，并引入探索率  $\varepsilon$ ，部分抽样使用完全随机抽样。
2. **复活间隔**：
   - 定期抽取权重低于保底值 $w_{min}$ 的网关重新测试，抽取数量为处于保底值的网关的 10%。

## 权重计算方法

采用指数移动平均 EMA 来计算可用性分数，相比于简单的成功率能表现网关的近况，并且也能在一定程度上反映网关历史可用的情况。

EMA 计算公式

（ $t$ 是测试的轮次； $S_t$ 取值 $1$ 或 $0$ ，表示本次成功或失败； $\alpha=\frac{2}{N+1}$ ， $N$ 是 EMA 窗口大小，此处取 `10`）

$$
\text{EMA}\_{t} = \alpha \cdot S_t +(1-\alpha) \cdot \text{EMA}\_{t-1}
$$

根据响应时间 $T$ （单位 `ms`）计算响应时间惩罚参数 $\gamma_\text{time}$，此处 $-k$ 取值为 $\rm{ln(0.8)}$ （最大惩罚 `0.8`）

$$
\gamma_\text{time} = e^{-k \cdot \frac{T}{1500}}
$$

根据下载速度 ${speed}$ （换算为 `KB/s`）计算下载速度惩罚参数 $\gamma_\text{speed}$ ，此处 $k$ 取值 $\frac{1}{0.7}-1$ （最大惩罚 `0.7`）

$$
\gamma_\text{speed} = (1+k\cdot e^{-\frac{speed}{1024}})^{-1}
$$

设置 $\beta$ 为平滑指数，此处取 `1.2` ，由此可算得平滑化且带保底权重的的权重 $w_t$

$$
w_t = max( \gamma_\text{time}\cdot \gamma_\text{speed} \cdot \text{EMA}\_t^\beta  , {w}_{min})
$$


---

### 一、基本定义

对于每个网关，在第 $t$ 次测试时：

1. 状态码成功判定函数：

$$
S_t = \begin{cases} 
1 & \text{if status\\_code} = 206 \\
0 & \text{otherwise}
\end{cases}
$$

2. 响应时间限制：

$$
T_t = \min(\text{response\\_time}, 1500)
$$

其中 response_time 是实际测试获得的响应时间（单位：`ms`）

### 二、EMA计算

EMA（指数移动平均）用于平滑状态码成功率：

1. EMA 衰减因子：

$$
\alpha = \frac{2}{N+1}
$$

其中历史窗口大小 $N=10$ 

2. EMA 递推公式：

$$
\text{EMA}\_t = \alpha \cdot S_t + (1-\alpha) \cdot \text{EMA}_{t-1}
$$

初始值：$\text{EMA}_0 = 1.0$

### 三、响应时间惩罚系数

1. 基准惩罚系数：

$$
k_{time} = -\ln(0.8)
$$

2. Gamma time计算：

$$
\gamma_{time} = e^{-k \cdot T_t/1500}
$$

### 四、下载速度惩罚系数

1. 下载速度惩罚系数

$$
k_{speed} = \frac{1}{0.7}-1
$$

2. Gamma speed 计算：

$$
\gamma_{speed} = \frac{1}{1+k\cdot e^{-speed/1024}}
$$



### 五、最终权重计算

1. 基础权重（对EMA进行幂次加权）：

$$
w_{base} = \text{EMA}_t^\beta
$$

其中 $\beta = 1.2$ 是权重平滑指数

2. 应用响应时间惩罚：

$$
w_t = \max(w_{base} \cdot \gamma_t, w_{min})
$$

其中 $w_{min} = 0.01$ 是最小权重值

### 五、权重的意义解释

1. EMA部分 $(\text{EMA}_t^\beta)$：
   - 反映网关的历史成功率
   - β > 1 使得分数对成功/失败更敏感
   - EMA确保了历史表现的平滑过渡

2. 响应时间惩罚 $(\gamma_t)$：
   - 当响应时间为0时， $\gamma_t = 1$
   - 当响应时间为1500ms时， $\gamma_t = 0.8$
   - 呈指数衰减，惩罚慢速响应

3. 最小权重保护 $(w_{min})$：
   - 确保所有网关有被选中的机会
   - 防止权重降为0后无法恢复

### 六、整体评分特点

1. 权重范围：

$$
w_{min} \leq w_t \leq 1
$$

2. 最佳评分条件：
   - $S_t = 1$ (206状态码)
   - $T_t \approx 0$ (快速响应)
   - 历史表现稳定（高EMA）

3. 最差评分条件：
   - $S_t = 0$ (非206状态码)
   - $T_t \geq 1500$ (慢速响应)
   - 历史表现不佳（低EMA）



EMA 计算： $$\text{EMA}\_t = \alpha \cdot S_t + (1-\alpha) \cdot \text{EMA}_{t-1}$$

响应时间惩罚： $$\gamma = e^{-k \cdot \frac{T}{1500}}$$

最终权重： $$w_{final} = \max(\text{EMA}\_t^\beta \cdot \gamma, w_{min})$$
