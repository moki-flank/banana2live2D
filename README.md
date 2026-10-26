# banano2live2D 🍌➡️🎭

> **轻量级双模型驱动（生图 + 多模态视觉文本模型）组件化 Live2D 生成器**  
> 原生支持 **【纯文本生成 Live2D (文生图 Text-to-Live2D)】** 与 **【参考图生成 Live2D (图生图 Image-to-Live2D)】**！  
> 原生支持 **【单张 3×3 九宫格语义组件拆件】+【自适应波谷切分 & BFS 边缘去底抠图】**！  
> 原生支持 **【多模态模型视觉配准 + 用户自定义动作 (.motion3.json) 生成】**！  
> 全面对齐《碧蓝航线》(Azur Lane `banerwei_3`) 标准 28 参数、4 节点物理摆动与 19+ 组动作规范，内置交互式 Web Studio 舞台！

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![Web Studio](https://img.shields.io/badge/Web%20Studio-Interactive%202.5D-blueviolet.svg)](web/index.html)
[![API Platform](https://img.shields.io/badge/API%20Platform-HrioAPI-orange.svg)](https://hrioapi.hrio.site)

---

## 🌟 效果展示 (Demo Showcase)

> 示例输入提示词（纯文本模式）：  
> `“银白发红瞳猫耳女仆，黑色蕾丝围裙女仆装，粉色蝴蝶结铃铛项圈，增加一个开心地跳起来挥手打招呼的动作”`

| 1. `gemini-nano-banana-2.1` 生成 3×3 语义组件九宫格 | 2. 自适应切分 + BFS 去底抠图 9 部件总览图 | 3. `gemini-3.8-flash` 视觉配准与动作装配成品 |
| :---: | :---: | :---: |
| <img src="examples/catmaid_3x3_sheet.jpg" width="280" alt="3x3组件九宫格" /> | <img src="examples/catmaid_matted_sheet.jpg" width="280" alt="去底抠图总览" /> | <img src="examples/catmaid_composite_preview.png" width="280" alt="装配成品预览" /> |

---

## 🚀 核心流水线：四步顺序组件化生成架构

本项目不依赖重型 3D 渲染管线或商业编辑器，核心生成完全由 **生图大模型 (`gemini-nano-banana-2.1`) + 轻量几何切分抠图算法 + 视觉多模态大模型 (`gemini-3.8-flash`)** 严格按序驱动：

### Step 1️⃣：调用生图模型 (`gemini-nano-banana-2.1`) 生成单张 3×3 九宫格组件图
* **文生图模式 (Text-to-Image)**：未上传图片附件时，100% 忠实根据用户输入的文本提示词生成角色拆件九宫格；
* **图生图模式 (Image-to-Image)**：上传角色立绘/人设参考图后，锁定参考图的角色外观特征拆解为 3×3 九宫格部件；
* **严格 9 宫格语义分区**：
  * `[0,0] hair_back`（后发主体） | `[0,1] body_torso`（无手臂躯干与服装主体） | `[0,2] head_base`（无五官空白脸型与脖子基底）
  * `[1,0] arm_left`（左臂与左手拆件） | `[1,1] arm_right`（右臂与右手拆件） | `[1,2] face_eyes`（左右眼 + 眉毛 + 闭眼态）
  * `[2,0] face_mouth_brows`（嘴型 + 腮红高光） | `[2,1] hair_front_side`（前刘海 + 两侧鬓发） | `[2,2] accessories`（头饰/猫耳/领结/舰装挂件）

### Step 2️⃣：自适应波谷切分 + BFS 洪水填充去底抠图 (`banano2gif` + `see-through-main`)
* **自适应投影波谷切分 (`cutter/slicer.py`)**：在 1/3、2/3 附近扫描像素梯度波谷定位分割线，防止截断发梢或袖口；
* **BFS 角落洪水填充去底 + 边缘 Halo 脱色净化 (`cutter/cleaner.py`)**：借鉴 `see-through-main` 的前景 Alpha 估计与连通域去噪，剥离纯白背景并打包生成 `2048×2048` 纹理图集 `textures/texture_00.png` 与 9 部件编号总览图 `matted_contact_sheet.jpg`。

### Step 3️⃣：调用多模态模型 (`gemini-3.8-flash`) 视觉配准 + 自定义动作生成
* 将 **抠图后的 9 部件编号总览图 + 各组件像素尺寸 + 用户原始提示词** 统一发送给 `gemini-3.8-flash`：
  1. **视觉配准 (`rig_spec`)**：自动推理每个部件在立绘画布上的装配坐标 `(anchor_x, anchor_y, scale)`、旋转枢轴 `(pivot_x, pivot_y)`、深度顺序 `z_order` 与弹簧阻尼；
  2. **自定义动作算法 (`custom_motions`)**：当用户在提示词中要求增加特定动作（如“开心地跳起来挥手打招呼”）时，自动合成对应的多关键帧动画曲线并编译为 `.motion3.json` 动作文件。

### Step 4️⃣：生成完整《碧蓝航线》(`banerwei_3`) 规范 Live2D 工程与交互舞台
* `<name>.model3.json`（含 `HitAreas`: `Head` / `Special` / `Body`，以及 `EyeBlink` / `LipSync` 参数组）
* `<name>.cdi3.json`（28 项标准控制参数 + 15 个 Part 分组）
* `<name>.physics3.json`（4 节点钟摆物理链：后发、前发、双臂、配饰丝带）
* `motions/*.motion3.json`（19 组标准 Cubic Bezier 动作 + 用户自定义动作 `custom_*.motion3.json`）

---

## 🔑 获取与配置 API Key

本项目内置零依赖原生 SDK，直连 **HrioAPI** 平台（支持 `gemini-nano-banana-2.1` 与 `gemini-3.8-flash`）：

1. 前往官方网站获取 API Key：👉 **[https://hrioapi.hrio.site](https://hrioapi.hrio.site)**
2. 在项目根目录创建 `.env` 文件或设置环境变量：
   ```bash
   # Windows PowerShell
   $env:HRIO_API_KEY="sk-xxxxxxxxxxxxxxxx"

   # Linux / macOS
   export HRIO_API_KEY="sk-xxxxxxxxxxxxxxxx"
   ```

---

## 🖥️ 快速开始 (Quick Start)

### 方式一：启动交互式 Web Studio（推荐）

```bash
pip install -r requirements.txt
python main.py studio --port 8090
```

启动后在浏览器访问：**http://127.0.0.1:8090**

* **文生图生成 Live2D**：不上传附件，直接在对话框输入角色外貌与动作要求（例如：`银白发红瞳猫耳女仆，增加一个跳起来挥手打招呼的动作`），点击 **「🚀 1.生图 ➔ 2.抠图 ➔ 3.文本模型生成动作 ➔ 装配」**；
* **图生图生成 Live2D**：点击 **「📎 上传参考图」** 上传角色图片，自动切换为 `图生图 (Image-to-Image)` 模式生成专属九宫格并完成装配；
* **一键导出工程**：点击右上角 **「📦 导出完整 Live2D 工程 (.zip)」** 下载包含全部 `.model3.json`、`.physics3.json`、`.cdi3.json`、`motions/*.motion3.json` 与 `parts/*.png` 的完整工程包。

### 方式二：命令行 CLI 生成

```bash
# 1. 纯文本生成完整 Live2D 工程并启动预览
python main.py create -p "银白发红瞳猫耳女仆，增加一个开心跳跃挥手的动作" -n catmaid -o output/catmaid --serve

# 2. 参考图 (图生图) 生成 Live2D 工程
python main.py create -i "my_character.png" -p "保持角色外貌，拆解为九宫格并增加敬礼动作" -n my_char -o output/my_char

# 3. 从已有的 3×3 九宫格拆件图直接切分抠图并装配
python main.py from-grid examples/catmaid_3x3_sheet.jpg -n catmaid -o output/catmaid
```

---

## 📂 项目目录结构

```text
banano2live2D/
├── banano2live2D/
│   ├── sdk/client.py           # 原生 HrioAPI 双模型客户端 (gemini-nano-banana-2.1 & gemini-3.8-flash)
│   ├── prompts/engine.py       # 3×3 九宫格组件化拆件 Prompt 引擎（支持纯文本与图生图）
│   ├── cutter/
│   │   ├── slicer.py           # 自适应投影波谷 3×3 切分算法
│   │   ├── cleaner.py          # BFS 洪水填充去底、Halo 净化与 2048 纹理图集打包
│   │   └── matting.py          # 边缘羽化与 Alpha 通道提取
│   ├── rigger/
│   │   ├── gemini_rigger.py    # gemini-3.8-flash 视觉配准 + 自定义动作规格生成
│   │   ├── motion_builder.py   # 19 组标准动作 + 用户自定义动作 (.motion3.json) 编译器
│   │   └── model_builder.py    # .model3.json / .cdi3.json / .physics3.json 生成器
│   └── viewer/
│       └── studio_server.py    # 四步顺序流水线后端服务与 ZIP 工程导出接口
├── web/index.html              # 交互式 Live2D Studio 前端界面 (2.5D 物理舞台 + 产物检查器)
├── examples/                   # 示例九宫格拆件图、去底总览图与成品预览图
├── main.py                     # CLI 入口
└── requirements.txt            # 轻量依赖 (Pillow, NumPy)
```

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。