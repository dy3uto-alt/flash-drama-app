import streamlit as st
import pandas as pd
from pyairtable import Api
from openai import OpenAI
import random

# --- 1. 页面配置 ---
st.set_page_config(page_title="⚡️闪剧生成器", page_icon="🎬", layout="wide")

# --- 2. 获取 API Keys (从 Secrets 获取) ---
# 我们稍后会在 Streamlit 后台配置这些钥匙，不要直接写在这里
try:
    AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    TABLE_ID = st.secrets["AIRTABLE_TABLE_ID"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except:
    st.error("请先在 Streamlit Cloud 设置 Secrets！")
    st.stop()

# --- 3. 初始化连接 ---
api = Api(AIRTABLE_TOKEN)
table = api.table(BASE_ID, TABLE_ID)
# 增加 base_url 参数，指向 DeepSeek
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.deepseek.com")

# --- 4. 侧边栏：控制台 ---
with st.sidebar:
    st.title("🎛️ 导演控制台")
    st.markdown("---")
    
    # 输入话题
    topic = st.text_input("1. 输入热点话题/情绪", "不想上班，想发疯")
    
    # 难度筛选 (从 Airtable 数据筛选)
    difficulty_filter = st.selectbox(
        "2. 拍摄难度限制",
        ["All (所有难度)", "Low (低成本穷鬼模式)", "Medium (进阶模式)"]
    )
    
    # 风格倾向
    style_mood = st.selectbox(
        "3. 风格倾向",
        ["随机 (Surprise Me)", "荒诞/搞笑", "压抑/冷酷", "暴力美学", "浪漫/唯美"]
    )
    
    st.markdown("---")
    st.caption("⚡️ Flash Drama Generator v1.0")

# --- 5. 主界面 ---
st.title("⚡️ 闪剧脚本生成器")
st.markdown(f"当前任务：为 **“{topic}”** 生成碎片化影像脚本")

# 核心逻辑函数：从 Airtable 拿数据
@st.cache_data(ttl=600) # 缓存10分钟，避免频繁消耗 API
def fetch_data():
    # 获取所有数据
    records = table.all()
    # 转换为 DataFrame 方便处理
    data = []
    for r in records:
        fields = r['fields']
        data.append({
            "Action Name": fields.get("Action Name"),
            "Visual Description": fields.get("Visual Description"),
            "Emotion": fields.get("Emotion", []),
            "Difficulty": fields.get("Difficulty"),
            "Props": fields.get("Props"),
            "MJ Prompt": fields.get("MJ Prompt"),
            "Origin URL": fields.get("Original Trope URL")
        })
    return pd.DataFrame(data)

# 核心逻辑函数：调用 AI 重混
def remix_script(row, user_topic):
    prompt = f"""
    Role: 你是一位先锋短视频导演。
    Task: 基于用户话题和指定的动作符号，生成一个“闪剧”拍摄方案。
    
    Input:
    - 话题: {user_topic}
    - 动作符号: {row['Action Name']} ({row['Visual Description']})
    - 原始道具: {row['Props']}
    
    Constraints (必须遵守):
    1. 单镜头 (One Take)。
    2. 穷鬼美学：严禁后期特效，必须用“生活廉价道具”物理模拟所有视觉奇观。
    3. 风格：荒诞、错位。
    4. 字数：控制在 150 字以内。
    
    Output Format:
    请直接输出一段通过 Markdown 格式渲染的文本，包含：
    **🎥 画面与调度：** ...
    **🛠️ 穷鬼特效：** ...
    **🎭 演员状态：** ...
    """
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )
    return response.choices[0].message.content

# --- 6. 生成按钮逻辑 ---
if st.button("🚀 开始重混 (Remix)", type="primary"):
    with st.spinner("正在检索动作库并重混..."):
        # 1. 拿数据
        df = fetch_data()
        
        # 2. 筛选数据
        if difficulty_filter != "All (所有难度)":
            # 简单的关键词匹配筛选，比如只留 Low
            keyword = difficulty_filter.split(" ")[0] # 拿到 "Low"
            df = df[df['Difficulty'] == keyword]
        
        if df.empty:
            st.error("没有找到符合难度的动作，请尝试选择 All。")
            st.stop()
            
        # 3. 随机抽取 1 个动作 (未来可以做生成多个)
        # 这里加入风格筛选逻辑会更复杂，暂时先做随机，保证跑通
        selected_row = df.sample(1).iloc[0]
        
        # 4. AI 生成
        script_content = remix_script(selected_row, topic)
        
        # 5. 显示结果
        st.success("生成完毕！")
        
        # 显示大卡片
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader(f"🎬 {selected_row['Action Name']}")
                st.info(f"难度: {selected_row['Difficulty']}")
                st.markdown(f"**致敬出处:** [点击查看原始梗]({selected_row['Origin URL']})")
                st.markdown("---")
                st.caption("分镜参考 Prompt (可复制到 Midjourney):")
                st.code(selected_row['MJ Prompt'], language="text")

            with col2:
                st.markdown("### 📝 拍摄脚本")
                st.markdown(script_content)
