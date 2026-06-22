import asyncio, edge_tts, os, sys

async def test():
    try:
        text = "你好，我是晓晓，御姐温柔音测试"
        out = os.path.join(os.environ["TEMP"], "_edge_test3.mp3")
        c = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural", rate="-10%", pitch="-5Hz")
        await c.save(out)
        size = os.path.getsize(out)
        print(f"OK: {size} bytes -> {out}")
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
