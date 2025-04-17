#!/usr/bin/env python3
"""诗歌预处理工具，将当前目录下的txt文件转换为按作者分类的JSON格式"""

import json
import re
from collections import defaultdict
from pathlib import Path


class PoemPreprocessor:
    """诗歌预处理器"""

    def __init__(self):
        # 用于去重的集合
        self.poem_hashes = set()
        # 按作者分类的诗歌
        self.poems_by_author = defaultdict(list)

    def _get_poem_hash(self, content: str) -> str:
        """生成诗歌的唯一标识"""
        import hashlib

        normalized = "".join(content.split())
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def process_file(self, file_path: Path) -> None:
        """处理单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            # 提取作者和标题
            author = "未知作者"
            title = ""
            content_start = 0

            lines = content.split("\n")
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("作者："):
                    author = line[3:].strip()
                elif line.startswith("标题："):
                    title = line[3:].strip()
                elif line.startswith("正文："):
                    content_start = i + 1
                    break

            # 提取正文内容
            poem_content = "\n".join(lines[content_start:]).strip()

            # 如果内容不为空，添加到集合中
            if poem_content:
                poem_hash = self._get_poem_hash(poem_content)
                if poem_hash not in self.poem_hashes:
                    self.poem_hashes.add(poem_hash)
                    self.poems_by_author[author].append(
                        {"title": title, "content": poem_content}
                    )
                    print(f"✓ 已添加: {title}")

        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")

    def save_results(self, output_dir: Path) -> None:
        """保存处理结果"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存每个作者的诗歌
        for author, poems in self.poems_by_author.items():
            safe_author = re.sub(r'[\\/:*?"<>|]', "_", author)
            output_file = output_dir / f"summary_{safe_author}.json"

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"author": author, "poems": poems, "total": len(poems)},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(f"✓ 已保存 {len(poems)} 首诗歌 - {author}")


def main():
    """主函数"""
    preprocessor = PoemPreprocessor()

    # 使用tools目录下的poems_to_process
    current_dir = Path(__file__).parent
    poems_dir = current_dir / "poems_to_process"
    processed_dir = current_dir / "processed_poems"

    txt_files = []
    if poems_dir.exists():
        txt_files.extend(poems_dir.glob("*.txt"))

    if not txt_files:
        print("没有找到txt文件")
        print(f"请将txt文件放在 {poems_dir} 目录下")
        return

    # 处理文件并保存结果
    for file_path in txt_files:
        preprocessor.process_file(file_path)

    # 保存到processed_poems目录
    preprocessor.save_results(processed_dir)
    print(f"\n处理完成，输出目录: {processed_dir}")
    print("\n下一步:")
    print("1. 运行以下命令将诗歌导入到向量数据库:")
    print("   python poetry_vector_db.py")


if __name__ == "__main__":
    main()
