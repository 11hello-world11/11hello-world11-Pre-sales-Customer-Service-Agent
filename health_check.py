#!/usr/bin/env python
"""
项目健康检查脚本
用于验证项目的基本配置和功能是否正常
"""

import os
import sys


def check_python_version():
    print("=" * 60)
    print("检查 Python 版本...")
    print("=" * 60)
    version = sys.version_info
    print(f"当前 Python 版本: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 10:
        print("✅ Python 版本符合要求 (>= 3.10)")
        return True
    else:
        print("❌ Python 版本过低，需要 3.10 或更高版本")
        return False


def check_dependencies():
    print("\n" + "=" * 60)
    print("检查依赖库...")
    print("=" * 60)
    
    required_packages = [
        ("langchain", "langchain"),
        ("langchain_openai", "langchain-openai"),
        ("dotenv", "python-dotenv"),
        ("chromadb", "chromadb"),
        ("dashscope", "dashscope"),
    ]
    
    all_ok = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✅ {package_name} 已安装")
        except ImportError:
            print(f"❌ {package_name} 未安装，请运行: pip install {package_name}")
            all_ok = False
    
    return all_ok


def check_config():
    print("\n" + "=" * 60)
    print("检查配置文件...")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查 .env 文件
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        print("✅ .env 文件存在")
        
        from dotenv import load_dotenv
        load_dotenv(env_path)
        
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
        
        if deepseek_key:
            print("✅ DEEPSEEK_API_KEY 已配置")
        else:
            print("❌ DEEPSEEK_API_KEY 未配置")
        
        if dashscope_key:
            print("✅ DASHSCOPE_API_KEY 已配置")
        else:
            print("❌ DASHSCOPE_API_KEY 未配置")
    else:
        print("❌ .env 文件不存在")
    
    # 检查 QA_txt 目录
    qa_dir = os.path.join(base_dir, "QA_txt")
    if os.path.exists(qa_dir):
        print(f"✅ QA_txt 目录存在: {qa_dir}")
        txt_files = [f for f in os.listdir(qa_dir) if f.endswith(".txt")]
        print(f"   找到 {len(txt_files)} 个问答文件")
    else:
        print(f"❌ QA_txt 目录不存在: {qa_dir}")
    
    return True


def check_directories():
    print("\n" + "=" * 60)
    print("检查目录结构...")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    required_dirs = ["QA_txt", "img", "video"]
    
    for dir_name in required_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            print(f"✅ {dir_name}/ 目录存在")
            items = os.listdir(dir_path)
            print(f"   包含 {len(items)} 个文件/子目录")
        else:
            print(f"⚠️  {dir_name}/ 目录不存在")
    
    # 检查可选目录
    optional_dirs = ["chromadb", "logs", "sessions"]
    for dir_name in optional_dirs:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            print(f"✅ {dir_name}/ 目录存在")
        else:
            print(f"ℹ️  {dir_name}/ 目录不存在 (会在运行时自动创建)")
    
    return True


def main():
    print("\n" + "=" * 60)
    print("电商售前智能助手 - 项目健康检查")
    print("=" * 60)
    
    results = []
    results.append(("Python 版本", check_python_version()))
    results.append(("依赖库", check_dependencies()))
    results.append(("配置文件", check_config()))
    results.append(("目录结构", check_directories()))
    
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有检查通过！项目可以正常运行。")
        print("运行命令: python agent.py")
    else:
        print("⚠️  部分检查失败，请先解决上述问题。")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
