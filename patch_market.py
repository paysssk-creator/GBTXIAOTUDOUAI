import re

path = r"C:\Users\ADMIN\Desktop\GBT-local\desktop\app.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

market_code = r'''
@app.route("/api/market")
def mk():
    import urllib.request
    indices={"sh000001":"上证指数","sz399001":"深证成指","sz399006":"创业板指","sh000688":"科创50","sh000300":"沪深300","sz399005":"中小100"}
    codes=",".join(indices.keys())
    try:
        req=urllib.request.Request("http://hq.sinajs.cn/list="+codes,headers={"Referer":"https://finance.sina.com.cn"})
        raw=urllib.request.urlopen(req,timeout=5).read().decode("gbk")
        result=[]
        for line in raw.strip().split("\n"):
            m=re.search(r"(sh\d+|sz\d+)",line)
            if not m:continue
            code=m.group(0)
            pm=re.search(r'="(.+)"',line)
            if not pm:continue
            parts=pm.group(1).split(",")
            if len(parts)<4:continue
            name=indices.get(code,parts[0])
            price=float(parts[3]) if parts[3] else 0
            prev=float(parts[2]) if parts[2] else 0
            chg=round(price-prev,2)
            chgp=round(chg/prev*100,2) if prev else 0
            result.append({"code":code,"name":name,"price":price,"change":chg,"changePct":chgp})
        return jsonify({"indices":result,"updated":True})
    except Exception as e:
        return jsonify({"indices":[],"error":str(e),"updated":False})
'''

# Insert after chat endpoint
marker = 'return jsonify({"response":llm.chat(t),"provider":llm.prov,"model":llm.model})'
c = c.replace(marker, marker + market_code)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Patched OK,", len(c), "bytes")
