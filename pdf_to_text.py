#!/usr/bin/env python3
"""
PDF to Text Converter (with OCR support)
แปลงไฟล์ PDF เป็นข้อความ (.txt) - รองรับทั้ง text-based และ scanned PDF

Usage:
    python3 pdf_to_text.py <input.pdf>                  # บันทึกเป็น .txt ในโฟลเดอร์เดียวกัน
    python3 pdf_to_text.py <input.pdf> -o output.txt    # บันทึกเป็นไฟล์ที่กำหนด
    python3 pdf_to_text.py <input.pdf> -p 1,2,3         # เฉพาะหน้าที่กำหนด
    python3 pdf_to_text.py <input.pdf> --pages 1-5      # ช่วงหน้าที่กำหนด
    python3 pdf_to_text.py <input.pdf> --lang tha+eng   # ระบุภาษา OCR
    python3 pdf_to_text.py <folder>                      # แปลงทุก PDF ในโฟลเดอร์
"""

import sys
import os
import argparse
import tempfile
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image


def parse_page_range(page_str, total_pages):
    pages = set()
    for part in page_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            start = max(1, int(start.strip()))
            end = min(total_pages, int(end.strip()))
            pages.update(range(start - 1, end))
        else:
            p = int(part.strip())
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(pages)


def extract_text_pdfplumber(input_path, target_pages):
    """ลอง extract ด้วย pdfplumber ก่อน (text-based PDF)"""
    results = []
    with pdfplumber.open(input_path) as pdf:
        for i in target_pages:
            page = pdf.pages[i]
            text = page.extract_text()
            results.append((i, text))
    return results


def extract_text_ocr(input_path, target_pages, lang='tha+eng', dpi=300):
    """ใช้ OCR สำหรับ scanned/image PDF"""
    results = []
    doc = fitz.open(input_path)
    for i in target_pages:
        page = doc[i]
        # Render page to image
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # OCR
        text = pytesseract.image_to_string(img, lang=lang)
        results.append((i, text.strip()))
    doc.close()
    return results


def pdf_to_text(input_path, output_path=None, pages=None, lang='tha+eng'):
    if not os.path.exists(input_path):
        print(f"❌ ไม่พบไฟล์: {input_path}")
        return False

    try:
        with pdfplumber.open(input_path) as pdf:
            total_pages = len(pdf.pages)
        print(f"📄 ไฟล์: {os.path.basename(input_path)}")
        print(f"   จำนวนหน้าทั้งหมด: {total_pages}")

        if pages:
            target_pages = parse_page_range(pages, total_pages)
            print(f"   หน้าที่เลือก: {pages}")
        else:
            target_pages = list(range(total_pages))

        # ลอง text-based ก่อน
        results = extract_text_pdfplumber(input_path, target_pages)
        has_text = any(t for _, t in results)

        if has_text:
            print("   ✅ พบข้อความใน PDF (text-based)")
            text_parts = [f"--- Page {i + 1} ---\n{text}" for i, text in results if text]
        else:
            print("   🔍 ไม่พบข้อความ — กำลังใช้ OCR (scanned PDF)...")
            results = extract_text_ocr(input_path, target_pages, lang=lang)
            text_parts = [f"--- Page {i + 1} ---\n{text}" for i, text in results if text]

        full_text = '\n\n'.join(text_parts)

        if not full_text.strip():
            print("   ⚠️ ไม่พบข้อความใดๆ ในเอกสาร")
            return False

        if not output_path:
            base = os.path.splitext(input_path)[0]
            output_path = base + '.txt'

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        print(f"✅ แปลงสำเร็จ! บันทึกที่: {output_path}")
        print(f"   จำนวนหน้าที่แปลง: {len(target_pages)}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def batch_convert(folder_path, output_dir=None, lang='tha+eng'):
    if not os.path.isdir(folder_path):
        print(f"❌ ไม่พบโฟลเดอร์: {folder_path}")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("❌ ไม่พบไฟล์ PDF ในโฟลเดอร์นี้")
        return

    print(f"📁 พบไฟล์ PDF {len(pdf_files)} ไฟล์")
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    success = 0
    for pdf_file in sorted(pdf_files):
        input_path = os.path.join(folder_path, pdf_file)
        if output_dir:
            base = os.path.splitext(pdf_file)[0]
            out_path = os.path.join(output_dir, base + '.txt')
        else:
            out_path = None
        print()
        if pdf_to_text(input_path, out_path, lang=lang):
            success += 1

    print(f"\n🎉 แปลงเสร็จสิ้น: {success}/{len(pdf_files)} ไฟล์")


def main():
    parser = argparse.ArgumentParser(
        description='PDF to Text Converter - แปลงไฟล์ PDF เป็นข้อความ (รองรับ OCR)'
    )
    parser.add_argument('input', help='ไฟล์ PDF หรือโฟลเดอร์ที่มี PDF')
    parser.add_argument('-o', '--output', help='ชื่อไฟล์ output (.txt)')
    parser.add_argument('-p', '--pages', help='หน้าที่ต้องการ (เช่น 1,2,3 หรือ 1-5)')
    parser.add_argument('-l', '--lang', default='tha+eng', help='ภาษา OCR (default: tha+eng)')
    parser.add_argument('-d', '--output-dir', help='โฟลเดอร์เก็บผลลัพธ์ (สำหรับ batch)')

    args = parser.parse_args()

    if os.path.isdir(args.input):
        batch_convert(args.input, args.output_dir, args.lang)
    else:
        success = pdf_to_text(args.input, args.output, args.pages, args.lang)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
