import streamlit as st
import pandas as pd
from pyairtable import Api
from openai import OpenAI
import random

# --- 1. 页面配置 ---
st.set_page_config(page_title="⚡️闪剧生成器 (Pro)", page_icon="🎬", layout="wide")

# --- 2. 获取 API Keys ---
try:
    # 优先尝试从 Secrets 获取
    AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    TABLE_ID = st.secrets["AIRTABLE_TABLE_ID"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("请在 Streamlit Cloud 设置 Secrets！")
    st.stop()

# --- 3. 初始化连接 ---
api = Api(AIRTABLE_TOKEN)
table = api.table(BASE_ID, TABLE_ID)

# 自动判断是 DeepSeek 还是 OpenAI (根据你 secrets 填的 key 决定，这里代码通用)
# 如果你用的是 DeepSeek/硅基流动，记得在 Secrets 里改 Key，这里代码不用动
# 为了兼容性，如果你用 DeepSeek，建议显式指定 base_url
BASE_URL = "https://api.deepseek.com" # 如果是用 OpenAI，请把这行删掉或改为 None
# BASE_URL = "https://api.siliconflow.cn/v1" # 如果是硅基流动

if "sk-" in OPENAI_API_KEY: 
    # 简单的判断，实际部署时请确保 base_url 和 key 匹配
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=BASE_URL)
else:
    client = OpenAI(api_key=OPENAI_API_KEY)


# --- 4. 侧边栏：导演控制台 ---
with st.sidebar:
    st.header("🎛️ 导演控制台")
    
    # 输入话题
    topic = st.text_area("1. 输入热点话题/情绪", "过年回家被催婚，想发疯", height=100)
    
    # 风格滤镜
    style_mood = st.selectbox(
        "2. 风格倾向",
        ["随机 (Surprise Me)", "荒诞/黑色幽默", "压抑/冷酷", "暴力美学", "浪漫/唯美"]
    )
    
    # 生成按钮
    generate_btn = st.button("🚀 开始重混 (Remix)", type="primary")
    
    st.markdown("---")
    st.caption("Flash Drama Generator v1.5")

# --- 5. 主界面 ---
st.title("⚡️ 闪剧脚本生成器")

# 核心函数：获取数据
@st.cache_data(ttl=600)
def fetch_data():
    records = table.all()
    data = []
    for r in records:
        fields = r['fields']
        # 做了容错处理，防止字段不存在报错
        data.append({
            "Action Name": fields.get("Action Name", "未知动作"),
            "Visual Description": fields.get("Visual Description", "无描述"),
            "Props": fields.get("Props", "无道具"),
            "Difficulty": fields.get("Difficulty", "Low"),
            "Origin URL": fields.get("Original Trope URL", "#")
        })
    return pd.DataFrame(data)

# 核心函数：AI 重混 (加入符号提取逻辑)
def remix_script(row, user_topic, style):
    prompt = f"""
    Role: 你是一位先锋短视频导演。
    
    Task: 将用户给定的【话题】强行植入到指定的【动作符号】中，生成一个“闪剧”拍摄方案。
    
    Input Data:
    - 话题/情绪: "{user_topic}"
    - 风格倾向: "{style}"
    - 基础动作符号: "{row['Action Name']}"
    - 动作视觉描述: "{row['Visual Description']}"
    - 原始道具建议: "{row['Props']}"
    
    Step-by-Step Thinking:
    1. **符号解码：** 先分析这个“基础动作”的经典之处（Iconic Element）在哪里？（比如：如果是泰坦尼克号，经典在于双臂张开；如果是无间道，经典在于指头）。
    2. **错位重组：** 保持这个“经典动作”不变，但把里面的道具和人物动机，替换成"{user_topic}"相关的元素。
    3. **穷鬼化：** 所有特效必须用廉价生活用品模拟。

    Output Format (Markdown):
    请直接输出脚本卡片内容：
    
    ### 🎬 剧名：[结合话题起个怪名字]
    
    **👁️ 视觉符号 (The Hook):**
    [一句话描述这是什么动作的变体，例如：致敬《无间道》天台，但拿的是辣条]
    
    **🎥 单镜头调度:**
    [详细描述画面。谁？在哪里？做了什么？必须保留原动作的经典特征！]
    
    **🛠️ 穷鬼特效/道具:**
    *   **核心道具:** [...替换为生活用品]
    *   **操作:** [...如何使用]
    
    **🎭 演员状态:**
    [面瘫/极度夸张/抽搐]
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat", # 如果用 OpenAI 改为 gpt-4o-mini
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9 # 高一点，让创意更疯一点
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 生成出错: {e}"

# --- 6. 业务逻辑 ---
if generate_btn:
    if not topic:
        st.warning("请输入话题！")
        st.stop()
        
    with st.spinner("正在从资产库提取符号..."):
        df = fetch_data()
        
        if df.empty:
            st.error("Airtable 里没有数据！请先去 Make 跑一点数据出来。")
            st.stop()
            
        # 随机抽取 1 个动作 (模拟“洗牌”)
        selected_row = df.sample(1).iloc[0]
        
    # 显示抽中的卡
    st.success(f"匹配到动作符号：**{selected_row['Action Name']}**")
    
    with st.spinner("AI 导演正在重混脚本..."):
        script = remix_script(selected_row, topic, style_mood)
        
        # 展示结果
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("📦 原始素材")
                st.markdown(f"**动作:** {selected_row['Action Name']}")
                st.caption(selected_row['Visual Description'])
                st.markdown(f"**难度:** {selected_row['Difficulty']}")
                st.markdown(f"[查看原始出处]({selected_row['Origin URL']})")
                
            with col2:
                st.markdown(script)
