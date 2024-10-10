import os
import xml.etree.ElementTree as ET
import re
import logging
from typing import Optional

# ログ設定: エラーのみをログに記録
logging.basicConfig(
    filename='xml_to_markdown_errors.log',
    level=logging.ERROR,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

def sanitize_filename(name: str) -> str:
    """ディレクトリ名およびファイル名から無効な文字を削除または置換します。"""
    name = re.sub(r'^\[\d+\]\s*', '', name)
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def extract_text(element: ET.Element) -> str:
    """XML要素からテキストを抽出してクリーンアップします。"""
    return ' '.join(element.itertext()).strip()

def classify_file(filename: str) -> Optional[str]:
    """ファイル名の末尾がm, a, tかを判定し、分類キーを返します。"""
    match = re.search(r'([mat])\.xml$', filename.lower())
    if match:
        return match.group(1)
    return None

def create_markdown_file(markdown_path: str, content: str) -> None:
    """Markdownファイルを作成し、内容を書き込みます。"""
    try:
        os.makedirs(os.path.dirname(markdown_path), exist_ok=True)
        with open(markdown_path, 'w', encoding='utf-8') as md_file:
            md_file.write(content.strip())
    except OSError as e:
        logging.error(f"Markdownファイル作成エラー {markdown_path}: {e}")

def process_h4_elements(h3_element: ET.Element, classified_output: str) -> None:
    """<h4>要素を処理してMarkdownファイルを作成します。"""
    h4_elements = h3_element.findall('h4')
    for h4 in h4_elements:
        h4n = h4.find('h4n')
        if h4n is None or not h4n.text:
            continue
        h4_name = sanitize_filename(h4n.text)
        markdown_filename = f"{h4_name}.md"
        markdown_path = os.path.join(classified_output, markdown_filename)

        paragraphs = h4.findall('p')
        if not paragraphs:
            continue
        markdown_content = '\n\n'.join(
            extract_text(p) for p in paragraphs if extract_text(p)
        )

        create_markdown_file(markdown_path, markdown_content)

def process_h3_elements(h2_element: ET.Element, classified_output: str) -> None:
    """<h3>要素を処理してMarkdownファイルを作成します。"""
    h3 = h2_element.find('h3')
    if h3 is not None:
        h3n = h3.find('h3n')
        if h3n is not None and h3n.text:
            h3_folder = sanitize_filename(h3n.text)
            classified_output = os.path.join(classified_output, h3_folder)

            if h3.findall('h4'):
                process_h4_elements(h3, classified_output)
            else:
                # <h4>要素が存在しない場合は<h3>をファイル名にして<p>要素を処理
                markdown_filename = f"{sanitize_filename(h3n.text)}.md"
                markdown_path = os.path.join(classified_output, markdown_filename)

                paragraphs = h3.findall('p')
                if not paragraphs:
                    return
                markdown_content = '\n\n'.join(
                    f"{extract_text(p)}" for p in paragraphs if extract_text(p)
                )

                create_markdown_file(markdown_path, markdown_content)

def process_h2_elements(h1_element: ET.Element, classified_output: str) -> None:
    """<h2>要素を処理します。"""
    h2 = h1_element.find('h2')
    if h2 is not None:
        h2n = h2.find('h2n')
        if h2n is not None and h2n.text:
            h2_folder = sanitize_filename(h2n.text)
            classified_output = os.path.join(classified_output, h2_folder)
            process_h3_elements(h2, classified_output)

def process_h1_elements(h0_element: ET.Element, classified_output: str) -> None:
    """<h1>要素を処理します。"""
    h1 = h0_element.find('h1')
    if h1 is not None:
        h1n = h1.find('h1n')
        if h1n is not None and h1n.text:
            h1_folder = sanitize_filename(h1n.text)
            classified_output = os.path.join(classified_output, h1_folder)
            process_h2_elements(h1, classified_output)

def process_xml_file(xml_path: str, output_root: str) -> None:
    """単一のXMLファイルを処理し、適切なディレクトリ構造でMarkdownファイルに変換します。"""
    try:
        filename = os.path.basename(xml_path)
        classification = classify_file(filename)
        if classification is None:
            logging.error(f"ファイル {xml_path}: ファイル名が 'm.xml', 'a.xml', 't.xml' のいずれでもありません。")
            return

        tree = ET.parse(xml_path)
        root = tree.getroot()

        # 最上位ディレクトリ名を<h>要素から取得
        h_element = root.find('h')
        if h_element is None or not h_element.text:
            logging.error(f"ファイル {xml_path}: <h> 要素が欠如または空です。")
            return
        top_folder = sanitize_filename(h_element.text)

        # <ha> -> <han> 要素に移動
        ha_element = root.find('ha')
        if ha_element is None:
            logging.error(f"ファイル {xml_path}: <ha> 要素が欠如しています。")
            return
        han_element = ha_element.find('han')
        if han_element is None or not han_element.text:
            logging.error(f"ファイル {xml_path}: <han> 要素が欠如または空です。")
            return
        han_folder = sanitize_filename(han_element.text)

        # 分類キーに基づいて出力パスを決定
        classified_output = os.path.join(output_root, classification, top_folder, han_folder)

        # 階層を順に辿る: h0 -> h1 -> h2 -> h3
        h0 = ha_element.find('h0')
        if h0 is not None:
            h0n = h0.find('h0n')
            if h0n is not None and h0n.text:
                h0_folder = sanitize_filename(h0n.text)
                classified_output = os.path.join(classified_output, h0_folder)

            process_h1_elements(h0, classified_output)

    except ET.ParseError as e:
        logging.error(f"XML解析エラー {xml_path}: {e}")
    except FileNotFoundError as e:
        logging.error(f"ファイルが見つかりません {xml_path}: {e}")
    except PermissionError as e:
        logging.error(f"パーミッションエラー {xml_path}: {e}")
    except Exception as e:
        logging.error(f"ファイル {xml_path} の処理中に予期せぬエラーが発生しました: {e}")

def process_all_xml(input_folder: str, output_folder: str) -> None:
    """入力フォルダ内の全てのXMLファイルを処理し、Markdownに変換します。"""
    for root_dir, dirs, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.xml'):
                xml_path = os.path.join(root_dir, file)
                process_xml_file(xml_path, output_folder)

def main() -> None:
    """スクリプトのエントリーポイント."""
    import argparse

    parser = argparse.ArgumentParser(description="XMLファイルをMarkdownに変換し、ディレクトリ構造を保持します。")
    parser.add_argument("input_folder", help="XMLファイルが格納されているフォルダのパス。")
    parser.add_argument("output_folder", help="Markdownファイルを保存するフォルダのパス。")

    args = parser.parse_args()

    if not os.path.exists(args.input_folder):
        print(f"入力フォルダが存在しません: {args.input_folder}")
        exit(1)

    os.makedirs(args.output_folder, exist_ok=True)
    process_all_xml(args.input_folder, args.output_folder)

if __name__ == "__main__":
    main()