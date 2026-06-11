# -*- coding: utf-8 -*-
"""app.py - Tool Agent CLI"""

import sys
from agent_graph import run


def main():
    """CLI 入口：用户输入问题，Agent 自动决定是否调工具"""
    print("=" * 50)
    print("  Supervisor Agent")
    print("  [Code] [English] [Career]")
    print("=" * 50)
    print("Commands: /exit")
    print()

    while True:
        try:
            text = input("You > ").strip()
            if not text:
                continue
            if text == "/exit":
                print("Goodbye!"); break

            print("Agent > ", end="", flush=True)
            answer = run(text)
            print(answer)
            print()

        except KeyboardInterrupt:
            print(); print("Goodbye!"); break
        except Exception as e:
            print(f"[Error] {e}"); print()


if __name__ == "__main__":
    main()