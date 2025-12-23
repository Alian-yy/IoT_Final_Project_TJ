
#### A. 发布端 (Publisher) - 电脑A

- **你的理解：** 部署在电脑A，读取文件，有GUI界面，发布数据。

- **任务书确认：** 完全正确。
  
  - **数据源：** 必须从数据文件读取（模拟传感器）。
  
  - **格式：** 必须严格遵守图2中的JSON格式（温度、湿度、气压）。

#### B. 服务器端 (Server & Broker)

- **你的理解：** 部署MQTT Broker。

- **任务书确认：** 正确。建议使用 Mosquitto。


#### C. 订阅端与数据处理 (Subscriber & Processor) - 电脑B
  
  - **电脑B** 订阅原始数据 -> **电脑B** 收到数据 -> **电脑B** 本地存入数据库 -> **电脑B** 进行算法分析（拟合） -> **电脑B** GUI展示。
    
    

## 要求


1. **本地存储（关键）：** 任务书2.4明确要求“**进行本地存储**”。订阅端收到数据后，不能只画图，必须存进数据库（MySQL）。

2. **曲线拟合（难点）：** 任务书2.7要求“**模拟分析预测数据曲线与历史数据曲线具备良好的拟合**”。这意味着你不能只画一条折线图，你可能需要用算法（如最小二乘法、线性回归）画出一条预测趋势线。



## 流程

1. **电脑A（发布者）：** 读本地txt/json文件 -> 界面显示 -> 发送给 MQTT Broker。

2. **服务器（Broker）：** 只是转发，不动数据。

3. **电脑B（订阅者）：**
   
   - **第一步：** 接收 Broker 转发来的原始数据。
   
   - **第二步：** 存入本地数据库。
   
   - **第三步：** 算法处理（比对历史数据、做预测拟合）。
   
   - **第四步：** 界面上同时画出“实时数据”和“分析/预测曲线”。



## **全流程操作指南**。

### 架构拓扑图

为了让你不迷路，我们先明确数据流向：

1. **发布端 (Vue + mqtt.js):** 采集数据 -> 通过 `ws://` 协议发布到 Broker。
2. **Broker (Mosquitto):** 接收消息 -> 广播给所有订阅者（包括后端和订阅端前端）。
3. **后端 (FastAPI + AIOMySQL):** 订阅 Topic -> 收到消息 -> **处理逻辑** -> 存入 **MySQL**。
4. **订阅端 (Vue + mqtt.js):**

   * *实时数据：* 通过 `ws://` 监听 Broker，直接渲染图表（低延迟）。
   * *历史数据：* 通过 HTTP GET 请求 FastAPI 接口，查询 MySQL 中的历史记录。

---


### 第一步：服务器环境与 Broker 配置 (基础)

这是地基。你需要配置 Mosquitto 同时支持 TCP（给后端用）和 WebSockets（给前端用）。

1. **修改 `mosquitto.conf`：**
   找到你的配置文件，必须包含以下内容（注意端口）：

   ````conf
   # 1. 标准 TCP 监听器 (给 FastAPI/Python 用)
   listener 1883
   ```protocol mqtt
   allow_anonymous true

   # 2. WebSocket 监听器 (给 Vue/mqtt.js
   ``` 用)
   listener 9001
   protocol websockets
   allow_anonymous true
   ````

2. **启动 Broker：**
   `mosquitto -c mosquitto.conf -v`
   *确保防火墙开放了 1883 和 9001 端口。*

---

### 第二步：数据库设计 (MySQL，订阅端，电脑B)

在 MySQL 中创建一个简单的表来存储传感器数据。

```sql
CREATE DATABASE iot_project;
USE iot_project;

CREATE TABLE sensor_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(50),
    temperature FLOAT,
    humidity FLOAT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

### 第三步：后端开发 (FastAPI + MQTT + MySQL)

这里是系统的“大脑”。它负责**静默订阅** Broker 的数据，清洗并入库。

**技术栈安装**技术栈安装：**

```bash
pip install fastapi uvicorn aiomysql tortoise-orm fastapi-mqtt
```

**main.py 完整代码：**

```python
from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from tortoise import Tortoise, fields, run_async
from tortoise.models import Model
from tortoise.contrib.fastapi import register_tortoise
import json

app = FastAPI()

# --- 1. 数据库模型 (Tortoise ORM) ---
class SensorData(Model):
    id = fields.IntField(pk=True)
    device_id = fields.CharField(max_length=50)
    temperature = fields.FloatField()
    humidity = fields.FloatField()
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "sensor_data"

# --- 2. MQTT 配置 ---
mqtt_config = MQTTConfig(
    host="localhost", # 如果 Broker 在另一台机器，填服务器IP
    port=1883,        # 后端走 TCP 协议，更稳
    keepalive=60,
    username="",
    password=""
)

mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

# --- 3. MQTT 事件处理 (核心逻辑) ---

@mqtt.on_connect()
def connect(client, flags, rc, properties):
    print(f"Connected: {client}")
    # 后端启动时，自动订阅数据主题
    mqtt.client.subscribe("sensor/raw") 

@mqtt.on_message()
async def message(client, topic, payload, qos, properties):
    """
    这里是后端处理逻辑的核心：
    1. 接收 Broker 转发来的原始数据
    2. 解析 JSON
    3. 进行业务逻辑判断 (比如报警)
    4. 存入 MySQL
    """
    try:
        data = json.loads(payload.decode())
        print(f"收到数据: {topic} -> {data}")
        
        # 业务处理示例：如果温度过高，后端可以发布一条报警指令
        if data['temperature'] > 40:
            print("警告：温度过高！")
            # mqtt.client.publish("sensor/alert", "High Temp Alert!")

        # 异步存入 MySQL
        await SensorData.create(
            device_id=data['device_id'],
            temperature=data['temperature'],
            humidity=data['humidity']
        )
        print("数据已存入数据库")
        
    except Exception as e:
        print(f"数据处理错误: {e}")

# --- 4. API 接口 (供前端查询历史数据) ---
@app.get("/api/history")
async def get_history():
    # 查询最近 10 条数据
    return await SensorData.all().order_by('-id').limit(10)

# --- 5. 数据库挂载 ---
register_tortoise(
    app,
    db_url='mysql://root:password@localhost:3306/iot_project', # 改你的数据库密码
    modules={'models': ['main']},
    generate_schemas=True,
    add_exception_handlers=True,
)

# 启动命令: uvicorn main:app --reload
```

---

### 第四步：前端开发 (Vue + mqtt.js)

由于前端直接用 HTML 文件写比较长，这里提供**核心逻辑代码**，你可以直接嵌入 Vue 组件或 HTML 的 `<script>` 中。

前端连接 Broker **必须使用 WebSocket 端口 (9001)**。

#### 1. 发布端 (Publisher)

```html
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>

<div id="app">
    <h3>设备模拟器 (Publisher)</h3>
    <button @click="sendData">发送数据</button>
</div>

<script>
    const { createApp } = Vue
    const app = createApp({
        data() {
            return {
                client: null,
                device_id: "sensor_001"
            }
        },
        mounted() {
            // 连接 Broker 的 WebSocket 端口
            // 格式: ws://服务器IP:9001/mqtt
            this.client = mqtt.connect('ws://localhost:9001/mqtt')
            
            this.client.on('connect', () => {
                console.log('Publisher Connected to Broker!')
            })
        },
        methods: {
            sendData() {
                // 模拟数据
                const payload = {
                    device_id: this.device_id,
                    temperature: (20 + Math.random() * 10).toFixed(2),
                    humidity: (40 + Math.random() * 20).toFixed(2)
                }
                
                // 发布到 Topic
                this.client.publish('sensor/raw', JSON.stringify(payload))
                console.log('Sent:', payload)
            }
        }
    }).mount('#app')
</script>
```

#### 2. 订阅端 (Subscriber)

这个页面不仅展示实时数据，还可以在页面加载时去请求 FastAPI 获取历史数据。

```html
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
<script src="https://unpkg.com/axios/dist/axios.min.js"></script>

<div id="app">
    <h3>实时监控 (Subscriber)</h3>
    <p>当前温度: {{ currentData.temperature }} °C</p>
    <p>当前湿度: {{ currentData.humidity }} %</p>
    
    <h4>历史数据 (来自 MySQL)</h4>
    <ul>
        <li v-for="item in historyList">
            {{ item.timestamp }} - Temp: {{ item.temperature }}
        </li>
    </ul>
</div>

<script>
    const { createApp } = Vue
    const app = createApp({
        data() {
            return {
                client: null,
                currentData: { temperature: 0, humidity: 0 },
                historyList: []
            }
        },
        async mounted() {
            // 1. 初始化时，请求后端 API 获取历史数据
            await this.fetchHistory();

            // 2. 连接 MQTT 获取实时更新
            this.client = mqtt.connect('ws://localhost:9001/mqtt')
            
            this.client.on('connect', () => {
                console.log('Subscriber Connected!')
                this.client.subscribe('sensor/raw')
            })

            // 3. 实时接收处理
            this.client.on('message', (topic, message) => {
                const data = JSON.parse(message.toString())
                this.currentData = data
                // 这里可以把新数据unshift进historyList，实现无刷新列表更新
            })
        },
        methods: {
            async fetchHistory() {
                try {
                    // 请求 FastAPI 接口
                    const res = await axios.get('http://localhost:8000/api/history')
                    this.historyList = res.data
                } catch (e) {
                    console.error("API Error", e)
                }
            }
        }
    }).mount('#app')
</script>
```

---

### 全流程运行操作总结

1. **服务器：** 启动 Mosquitto (`mosquitto -c mosquitto.conf`).

   * *验证：* `netstat -an | grep 9001` 确认 WebSocket 端口开了。
2. **后端：** 启动 FastAPI (`uvicorn main:app --reload`).
   *  * *验证：* 此时控制台应该显示 `Connected: <MQTT Client>`，说明后端已经连上 Broker 并开始蹲守数据了。
3. **前端 - 发布端：** 浏览器打开 `publisher.html`，点击“发送数据”。
4. **观察效果：**

   * **发布端控制台：** 显示 `Sent: {...}`。
   * **后端控制台：** 应该立即打印 `收到数据: sensor`收到数据: sensor/raw -> {...}` 并提示 `数据已存入数据库`。
   * **数据库：** 刷新 MySQL 表，应该能看到新数据。
   * **前端 - 订阅端：** 页面上的数字应该会立即跳动（走的是 WebSocket 实时通道），不需要刷新页面。


# 分工

- 组员A — 服务器与 Broker（负责）  
  - 职责：部署并配置 Mosquitto（TCP 1883 + WebSocket 9001）、修改 `mosquitto.conf`、开防火墙端口并验证连通性。  
  - 交付：`mosquitto.conf`、启动脚本、端口验证截图/命令输出。

- 组员B — 发布端（电脑A）  
  - 职责：实现带 GUI 的发布端，按文档 JSON 格式从本地文件读取并通过 `ws://...:9001/mqtt` 发布到 `sensor/raw`。  
  - 交付：发布端代码/页面（`publisher.html` 或 Vue 组件）、使用说明、演示截图或视频。

- 组员C — 后端与数据处理（电脑B）  
  - 职责：在电脑B 上部署 FastAPI，使用 TCP 订阅 Broker，解析并清洗数据，存入 MySQL，完成拟合/预测算法（如线性回归或最小二乘），并提供历史数据 API。  
  - 交付：后端代码（`main.py`）、数据库建表 SQL、拟合算法说明与输出样例、接口文档与测试记录。

- 组员D — 订阅端前端与可视化（电脑B）  
  - 职责：实现订阅端前端（通过 WebSocket 显示实时数据、通过 HTTP 获取历史数据），绘制实时曲线与预测曲线，负责前后端联调。  
  - 交付：订阅端页面/组件、图表示例、联调记录与演示截图。

为了保持主题不变，我细化了C，D的任务：
- **总体原则（必须遵守）**  
  - 后端与订阅前端都部署在电脑B 上，后端通过 TCP（1883）订阅 Broker，前端通过 WebSocket（9001）显示实时数据并通过 HTTP 请求历史数据。  
  - 所有接口与数据格式遵循 modify.md 的 JSON 结构（device_id, temperature, humidity, timestamp 等），并在交接文档里写明示例 payload。  

- **组员C（后端 & 数据处理，电脑B）—— 任务拆解与交付**  
  1) 在电脑B 部署 FastAPI 并连接 Broker（当前 todo: `在电脑B部署FastAPI并订阅MQTT`，进行中）  
     - 工作项：搭建 Python 环境、安装依赖（fastapi, fastapi-mqtt/ paho-mqtt, aiomysql/tortoise-orm 等）、实现 mqtt 客户端订阅 `sensor/raw`（TCP）。  
     - 交付物：`main.py`（能启动并打印接收到的数据）、启动说明与依赖列表（requirements.txt）。  
     - 联调点：提供示例 payload 与本地调试命令，告知前端 websocket 地址与后端 HTTP 地址。  

  2) 设计并创建 MySQL 表结构（todo: `设计并创建MySQL传感器数据表`）  
     - 工作项：定义字段（id, device_id, temperature, humidity, pressure?, timestamp, raw_payload），写 SQL 建表脚本并在本地验证。  
     - 交付物：`create_tables.sql`、数据库访问配置说明。  

  3) 实现数据解析与清洗（todo: `实现数据解析与清洗逻辑`）  
     - 工作项：字段类型校验（temperature 数值、timestamp 格式）、缺失值处理、异常值过滤（物理合理范围校验）、日志记录。  
     - 交付物：清洗逻辑代码段、处理示例（原始 -> 清洗后），异常样例统计表。  

  4) 实现拟合 / 预测算法并产出样例（todo: `实现拟合/预测算法并输出样例`）  
     - 工作项：实现一到两种算法（线性回归、滑动平均或最小二乘拟合），实现接口供前端获取预测数据或后端生成并存为表字段。  
     - 额外：实现“舒适度分析”模块（可选但建议）：依据温湿度计算 PMV/舒适度指数或简单的舒适度评分规则。  
     - 交付物：算法代码、说明文档、对比图（历史真实 vs 拟合/预测曲线）、CSV/JSON 输出样例。  

  5) 实现历史数据与报警 API（todo: `实现历史数据与报警API`）  
     - 工作项：实现 `/api/history?limit=N`、`/api/predict?range=...`、可选 `/api/comfort?device=...`；实现简单报警规则并可返回告警记录。  
     - 交付物：接口文档（路径、参数、返回示例）、Postman/ curl 测试脚本、单元测试或集成测试记录。  

  6) 测试与文档  
     - 工作项：撰写后端 README（启动、配置、数据库、接口样例）、提供接收数据的控制台日志与入库截图。  
     - 交付物：README、调试日志截图、数据库表截图、接口响应样例。  

- **组员D（订阅端前端 & 可视化，电脑B）—— 任务拆解与交付**  
  1) 实现订阅端实时 WebSocket 显示（todo: `实现订阅端实时WebSocket显示`）  
     - 工作项：使用 mqtt.js 通过 `ws://<broker-ip>:9001/mqtt` 连接并订阅 `sensor/raw`，实时接收并在页面上显示当前温湿度与来源设备。  
     - 交付物：`subscriber.html` 或 Vue 组件（可打开即看实时数值）、实时接收控制台输出。  
     - 联调点：确认前端能接收后端通过 Broker 发出的消息；如果后端也订阅并转发测试消息，需联动测试。  

  2) 实现历史数据 HTTP 调用并绘制图表（todo: `实现历史数据HTTP调用并绘制图表`）  
     - 工作项：通过 Axios 请求后端 `/api/history`，用 ECharts/Chart.js 绘制时间序列图，支持切换设备与时间范围。  
     - 交付物：图表页面、图表交互说明（时间范围、缩放、导出 CSV 功能可加）。  

  3) 绘制预测曲线与舒适度可视化（todo: `绘制预测曲线与舒适度可视化`）  
     - 工作项：在同一图表上叠加后端返回的预测/拟合曲线；实现舒适度颜色带或单独面板显示舒适度指数与解释。  
     - 交付物：包含实时曲线、历史曲线与预测曲线的示例图，舒适度说明面板（阈值与解释）。  

  4) 前后端联调与用户交互优化（todo: `完成前后端联调并提交演示记录`）  
     - 工作项：与后端对接接口并验证数据一致性（时间戳、设备 id、数值单位）；编写联调记录（问题与解决办法）；实现基本错误处理（连接失败、API 超时提示）。  
     - 交付物：联调记录文档、演示截图/短视频、操作说明。
