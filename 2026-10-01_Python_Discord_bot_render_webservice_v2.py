# 2026-10-01_Python_Discord_bot_render_webservice_v2
import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from google import genai
from dotenv import load_dotenv

# 1. 載入 .env 檔案（本機開發時使用，Render 部署時由後台注入）
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 初始化 Gemini API 用戶端
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. 建立微型 Flask 伺服器（給 Render / UptimeRobot 檢查 HTTP 狀態）
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    return "Discord Bot is running smoothly!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==========================================
# 3. 設定與啟動 Discord Bot
# ==========================================
intents = discord.Intents.default()
intents.message_content = True  # 啟用訊息內容讀取權限

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot 已成功登入為：{bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# 修改位置：新增聊天紀錄分析與 Gemini AI 統計指令
# 修改原因：補全原專案的核心功能（抓取 Discord 頻道訊息並生成統計報告）
# 修改後預期效果：使用者輸入 !count_chat 30 時，Bot 會自動擷取 30 條訊息並用 Gemini 分析回傳
@bot.command()
async def count_chat(ctx, limit: int = 30):
    """
    指令格式：!count_chat 30
    抓取頻道最近 30 條訊息，並讓 Gemini 做統計與分析
    """
    if not gemini_client:
        await ctx.send("❌ 錯誤：尚未設定 GEMINI_API_KEY 環境變數！")
        return

    await ctx.send(f"正在讀取最近 {limit} 條聊天紀錄並進行統計...")

    # 抓取 Discord 頻道歷史紀錄
    messages = []
    async for msg in ctx.channel.history(limit=limit):
        if not msg.author.bot:  # 忽略機器人發送的訊息
            messages.append(f"{msg.author.name}: {msg.content}")

    if not messages:
        await ctx.send("沒有找到有效的成員聊天紀錄。")
        return

    chat_logs = "\n".join(messages)

    # 給 Gemini 的數據分析 Prompt
    prompt = f"""
    你是一個 Discord 數據分析 Agent。請分析以下成員的聊天紀錄，並完成以下任務：
    1. 統計每位成員發言的總次數（排序）。
    2. 總結這段聊天紀錄的主要討論話題（1-3 點）。
    3. 找出最活躍的成員與特別值得注意的互動。

    聊天紀錄內容如下：
    ---
    {chat_logs}
    ---
    """

    # 指數退避重試機制，處理 API 503 繁忙
    max_retries = 3
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
            )
            await ctx.send(response.text)
            break

        except Exception as e:
            error_msg = str(e)
            if ("503" in error_msg or "UNAVAILABLE" in error_msg) and attempt < max_retries:
                await ctx.send(f"Gemini API 伺服器繁忙 (503)，等待 {retry_delay} 秒後進行第 {attempt} 次自動重試...")
                await asyncio.sleep(retry_delay)
                retry_delay += 2
            else:
                await ctx.send(f"分析時發生錯誤（重試 {attempt} 次後失敗）：{e}")
                break

# 確保指令處理相容性
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# ==========================================
# 4. 程式執行入口
# ==========================================
if __name__ == "__main__":
    keep_alive()
    
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ 錯誤：找不到 DISCORD_BOT_TOKEN 環境變數！")
