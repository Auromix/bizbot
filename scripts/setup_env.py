#!/usr/bin/env python3
"""交互式生成 .env 配置文件

使用方式：
    python scripts/setup_env.py

会引导用户填写必要的配置项，生成 .env 文件。
"""
import os
import sys

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")


# 配置项定义：(env_key, 描述, 默认值, 是否必填)
CONFIG_ITEMS = [
    # === MiniMax LLM ===
    ("MINIMAX_API_KEY", "MiniMax API Key（必填，从 https://platform.minimaxi.com 获取）", "", True),
    ("MINIMAX_MODEL", "MiniMax 模型名称", "MiniMax-M2.5", False),
    ("MINIMAX_BASE_URL", "MiniMax API 地址（国内默认，国际用 https://api.minimax.io/anthropic）", "https://api.minimaxi.com/anthropic", False),

    # === 数据库 ===
    ("DATABASE_URL", "数据库连接地址", "sqlite:///data/store.db", False),

    # === Web 平台 ===
    ("WEB_HOST", "Web 监听地址", "0.0.0.0", False),
    ("WEB_PORT", "Web 监听端口", "8080", False),
    ("WEB_USERNAME", "Web 登录用户名", "admin", False),
    ("WEB_PASSWORD", "Web 登录密码", "admin123", False),
    ("WEB_SECRET_KEY", "Web JWT 密钥（建议修改为随机字符串）", "change-me-to-a-random-secret-key", False),

    # === 其他 ===
    ("CONFIDENCE_THRESHOLD", "LLM 解析置信度阈值", "0.7", False),
    ("DAILY_SUMMARY_TIME", "每日汇总时间", "21:00", False),
]


def main():
    print()
    print("=" * 60)
    print("  We-Business-Manager 配置向导")
    print("  生成 .env 配置文件")
    print("=" * 60)
    print()

    # 检查是否已存在 .env
    if os.path.exists(ENV_FILE):
        print(f"⚠️  检测到已有 .env 文件: {ENV_FILE}")
        choice = input("是否覆盖？(y/N): ").strip().lower()
        if choice != "y":
            print("已取消。")
            return
        print()

    # 收集配置
    env_lines = []
    env_lines.append("# We-Business-Manager 配置文件")
    env_lines.append("# 由 scripts/setup_env.py 自动生成")
    env_lines.append("")

    current_section = None

    for key, desc, default, required in CONFIG_ITEMS:
        # 根据前缀分组显示
        section = key.split("_")[0]
        if section != current_section:
            current_section = section
            env_lines.append("")
            section_names = {
                "MINIMAX": "# === MiniMax LLM 配置 ===",
                "DATABASE": "# === 数据库配置 ===",
                "WEB": "# === Web 平台配置 ===",
                "CONFIDENCE": "# === 其他配置 ===",
                "DAILY": "# === 其他配置 ===",
            }
            header = section_names.get(section, f"# === {section} ===")
            # 避免重复写同一个 section header
            if not env_lines or env_lines[-1] != header:
                env_lines.append(header)

        # 提示用户输入
        req_tag = " [必填]" if required else ""
        default_hint = f" (默认: {default})" if default else ""

        prompt = f"  {desc}{req_tag}{default_hint}\n  {key}= "
        print(f"📝 {desc}{req_tag}")

        while True:
            value = input(f"  {key}={default_hint}: ").strip()
            if not value:
                value = default
            if required and not value:
                print(f"  ❌ {key} 是必填项，请输入值。")
                continue
            break

        env_lines.append(f"{key}={value}")
        print()

    # 写入文件
    env_content = "\n".join(env_lines) + "\n"

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(env_content)

    print("=" * 60)
    print(f"  ✅ 配置文件已生成: {ENV_FILE}")
    print()
    print("  启动应用：")
    print("    python app.py")
    print()
    print("  或运行示例：")
    print("    python examples/therapy_agent_manager.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

