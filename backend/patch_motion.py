with open('ai_service/motion_liveness.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = "if len(history) >= 4 and elapsed >= 1.8:"
replacement = "if (len(history) >= 3 and elapsed >= 1.2) or elapsed >= 1.8:"

assert target in code, "Target not found"
code = code.replace(target, replacement)

with open('ai_service/motion_liveness.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("SUCCESS: Optimized spoof detection condition")
