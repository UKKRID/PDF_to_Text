#!/usr/bin/env python3
"""
PDF to Text Web Application
เครื่องมือแปลง PDF เป็นข้อความ พร้อม OCR ภาษาไทย
"""

import os
import uuid
import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def extract_text_pdfplumber(filepath, pages=None):
    results = []
    with pdfplumber.open(filepath) as pdf:
        total = len(pdf.pages)
        targets = pages if pages else list(range(total))
        for i in targets:
            if i < total:
                text = pdf.pages[i].extract_text()
                results.append((i, text))
    return results, total


def extract_text_ocr(filepath, pages=None, lang='tha+eng', dpi=200):
    results = []
    doc = fitz.open(filepath)
    total = len(doc)
    targets = pages if pages else list(range(total))
    for i in targets:
        if i < total:
            page = doc[i]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang=lang)
            results.append((i, text.strip()))
    doc.close()
    return results, total


def convert_pdf(filepath, pages=None, lang='tha+eng'):
    results, total = extract_text_pdfplumber(filepath, pages)
    has_text = any(t for _, t in results)

    if has_text:
        method = "text-based"
    else:
        method = "OCR"
        results, _ = extract_text_ocr(filepath, pages, lang=lang)

    text_parts = [f"--- Page {i + 1} ---\n{text}" for i, text in results if text]
    full_text = '\n\n'.join(text_parts)
    return full_text, total, method


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'pdf' not in request.files:
        return jsonify({'error': 'ไม่พบไฟล์ PDF'}), 400

    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'ไม่ได้เลือกไฟล์'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'ต้องเป็นไฟล์ .pdf เท่านั้น'}), 400

    pages_str = request.form.get('pages', '').strip()
    lang = request.form.get('lang', 'tha+eng')

    pages = None
    if pages_str:
        try:
            pages = []
            for part in pages_str.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = part.split('-', 1)
                    pages.extend(range(int(start) - 1, int(end)))
                else:
                    pages.append(int(part) - 1)
        except ValueError:
            return jsonify({'error': 'รูปแบบหน้าไม่ถูกต้อง (เช่น 1,2,3 หรือ 1-5)'}), 400

    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
    output_path = os.path.join(OUTPUT_FOLDER, f"{file_id}_{os.path.splitext(filename)[0]}.txt")

    file.save(input_path)

    try:
        full_text, total_pages, method = convert_pdf(input_path, pages, lang)

        if not full_text.strip():
            return jsonify({'error': 'ไม่พบข้อความในเอกสาร'}), 400

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        return jsonify({
            'success': True,
            'total_pages': total_pages,
            'converted_pages': len([p for p in (pages or range(total_pages))]),
            'method': method,
            'filename': os.path.splitext(filename)[0] + '.txt',
            'download_id': file_id,
            'preview': full_text[:2000]
        })

    except Exception as e:
        return jsonify({'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


@app.route('/download/<file_id>')
def download(file_id):
    for f in os.listdir(OUTPUT_FOLDER):
        if f.startswith(file_id):
            path = os.path.join(OUTPUT_FOLDER, f)
            return send_file(path, as_attachment=True, download_name=f.split('_', 1)[1])
    return jsonify({'error': 'ไม่พบไฟล์'}), 404


if __name__ == '__main__':
    print("🚀 PDF to Text Web App")
    print("📍 เปิดเว็บที่: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
