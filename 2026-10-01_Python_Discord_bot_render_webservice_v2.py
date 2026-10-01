# 2026-10-01_Python_Discord_bot_render_webservice_v2
import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from dotenv import load_dotenv

# 載入 .env 檔案（本機開發時使用，Render 部署時由後台注入）
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# 若有 Gemini API Key，同樣在此獲取：
# GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# ==========================================
# 1. 建立微型 Flask 伺服器（給 Render 檢查 HTTP 狀態）
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    # 只要外部發送 HTTP 請求造訪此路徑，回傳 200 OK 告知伺服器正常運作
    return "Discord Bot is running smoothly!", 200

def run_flask():
    # 獲取 Render 自動指派的 PORT 號（預設為 10000），若本機執行則預設使用 8080
    port = int(os.environ.get("PORT", 8080))
    # host="0.0.0.0" 才能讓 Render 外部存取
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    # 建立獨立的執行緒（Thread）來執行 Flask，避免阻塞 Discord Bot 主程式
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==========================================
# 2. 設定與啟動 Discord Bot
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

# ==========================================
# 3. 程式執行入口
# ==========================================
if __name__ == "__main__":
    # 先啟動背景 Flask Web Server
    keep_alive()
    
    # 再啟動 Discord Bot
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ 錯誤：找不到 DISCORD_BOT_TOKEN 環境變數！")


