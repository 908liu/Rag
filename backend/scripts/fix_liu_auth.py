"""重置 liu 密码并验证登录"""
import hashlib, secrets, sqlite3, requests

# 重置密码
salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac("sha256", "liu123456".encode(), salt, 310_000)
full_hash = f"{salt.hex()}${digest.hex()}"

conn = sqlite3.connect("d:/my_program/backend/data/app.db")
c = conn.cursor()
c.execute("SELECT id, username FROM users")
for row in c.fetchall():
    print(f"User id={row[0]} username={row[1]}")

c.execute("UPDATE users SET password_hash=? WHERE username=?", (full_hash, "liu"))
conn.commit()
conn.close()
print("Password reset to: liu123456")

# 验证登录
r = requests.post("http://localhost:8000/api/v1/auth/login", json={"username": "liu", "password": "liu123456"})
print(f"Login status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"Token OK, user_id={d['user']['id']}")
    print(f"Docs count: ", end="")
    h = {"Authorization": f"Bearer {d['token']}"}
    docs = requests.get("http://localhost:8000/api/v1/documents", headers=h).json()
    print(len(docs))
    for doc in docs:
        print(f"  doc#{doc['id']}: {doc.get('filename', '?')}")
else:
    print(f"Login failed: {r.text}")