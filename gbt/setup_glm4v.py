"""
GLM-4V Vision API 自动配置向导
=============================
1. 打开 https://open.bigmodel.cn/usercenter/apikeys 
2. 复制API Key 
3. 运行: python -m gbt.setup_glm4v --key YOUR_KEY
"""

import os, sys

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


def set_glm_key(api_key: str) -> bool:
    """设置GLM_API_KEY到.env文件"""
    if not api_key or len(api_key) < 20:
        print("❌ Key太短, 请复制完整的API Key (通常以 . 结尾)")
        return False

    # 写入.env
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")

    found = False
    new_lines = []
    for line in lines:
        if line.startswith("GLM_API_KEY="):
            new_lines.append(f"GLM_API_KEY={api_key}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"GLM_API_KEY={api_key}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    # 设环境变量
    os.environ["GLM_API_KEY"] = api_key

    print(f"✅ GLM_API_KEY 已配置 ({len(api_key)} chars)")
    return True


def test_glm_connection() -> bool:
    """测试GLM连接"""
    try:
        from gbt.llm import GBTLLM
        llm = GBTLLM(provider="zhipu", model="glm-4-flash",
                     timeout=30, max_tokens=50)
        resp = llm.invoke([{"role": "user", "content": "Say 'GLM OK' in Chinese"}])
        if resp and "OK" in resp or "GLM" in resp:
            print(f"✅ GLM连接成功: {resp[:50]}")
            return True
    except Exception as e:
        print(f"❌ GLM连接失败: {e}")
    return False


def test_glm4v_vision() -> bool:
    """测试GLM-4V视觉能力"""
    try:
        from gbt.llm import GBTLLM
        from gbt.autopilot import compress_for_vision
        from PIL import Image, ImageDraw

        # 创建测试图片
        img = Image.new("RGB", (400, 300), "white")
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "600519", fill="black")
        draw.rectangle([40, 80, 200, 130], outline="red", width=3)
        draw.text((50, 90), "买入 100股", fill="red")

        b64 = compress_for_vision(img, max_size=400)

        llm = GBTLLM(provider="zhipu", model="glm-4v",
                     timeout=60, max_tokens=200)
        resp = llm.chat_with_vision(
            "图中股票代码是多少? 按钮文字是什么? 简短回答",
            b64, ""
        )
        print(f"✅ GLM-4V视觉测试: {resp[:200]}")
        return True
    except Exception as e:
        print(f"❌ GLM-4V测试失败: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="GLM-4V 配置向导")
    parser.add_argument("--key", help="你的GLM API Key")
    parser.add_argument("--test", action="store_true", help="测试连接")
    parser.add_argument("--vision", action="store_true", help="测试视觉")
    args = parser.parse_args()

    if args.key:
        set_glm_key(args.key)
        test_glm_connection()

    if args.test:
        test_glm_connection()

    if args.vision:
        test_glm4v_vision()

    print("""
╔══════════════════════════════════════════╗
║   GLM-4V 配置步骤:                       ║
║   1. 打开 open.bigmodel.cn 注册/登录      ║
║   2. 创建API Key (5分钟)                 ║
║   3. 运行: python -m gbt.setup_glm4v     ║
║       --key YOUR_API_KEY                 ║
║   4. 运行: python -m gbt.setup_glm4v     ║
║       --vision                           ║
║                                          ║
║   新用户送2000万tokens 免费额度!          ║
╚══════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
