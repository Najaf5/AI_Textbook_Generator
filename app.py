import os
import re
from datetime import datetime
from groq import Groq
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import gradio as gr

# Initialize Groq API
client = Groq(api_key=os.environ["GROQ_API_KEY"])

# In-memory data store
book_data = {
    "title": "",
    "grade": "",
    "author": "",
    "medium": "English",
    "toc": [],
    "chapters": {},
    "preface": ""
}

# Clean formatting
def clean_formatting(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"[#•●→✅🔹🔸📘📖📑📤📥⬇️🎉>]", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()

# Generate Preface + TOC
def generate_book_intro(title, grade, author, medium):
    book_data["title"] = title.strip()
    book_data["grade"] = grade.strip()
    book_data["author"] = author.strip()
    book_data["medium"] = medium

    prompt = f"""
    You are a professional Pakistani educational author.
    Medium: {medium}.
    Write the following sections for a textbook titled: "{title}" for Grade {grade} by {author}:
    1. A formal preface aligned with APA 7th Edition style (Times New Roman, size 12, 1.5 spacing).
    2. A Table of Contents with 7 chapters. Each chapter should be meaningful for absolute beginners in Pakistan.
    Do NOT write chapter content. Only return:
    - Preface
    - Table of Contents
    """

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    output = response.choices[0].message.content.strip()
    preface, toc = output.split("Table of Contents", 1)
    book_data["preface"] = clean_formatting(preface)
    book_data["toc"] = [clean_formatting(line) for line in toc.strip().split('\n') if line.strip()]

    return f"Preface:\n\n{book_data['preface']}\n\nTable of Contents:\n\n" + "\n".join(book_data["toc"])

# Generate Chapter
def generate_chapter(ch_num):
    if ch_num in book_data["chapters"]:
        return book_data["chapters"][ch_num]

    ch_title = next((line for line in book_data["toc"] if line.startswith(str(ch_num))), f"Chapter {ch_num}")

    prompt = f"""
    Medium: {book_data['medium']}.
    Write Chapter {ch_num} for the book "{book_data['title']}" (Grade {book_data['grade']}) by {book_data['author']}.
    Chapter Title: {ch_title}

    Must include:
    - Student Learning Outcomes (5–7) at the start.
    - Detailed content aligned with each SLO.
    - For every concept, explain with What, Why, How examples (Pakistani context, beginners friendly).
    - Activities or Case Studies relevant to Pakistan.
    - Post-Assessment: 10 MCQs (no answers).
    - Glossary.

    Use APA style (Times New Roman, font 12, line spacing 1.5). 
    Do NOT use symbols/emojis.
    """

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    chapter = clean_formatting(response.choices[0].message.content.strip())
    book_data["chapters"][ch_num] = chapter
    return chapter

# Export to Word
def export_book_word():
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)

    def add_paragraph(text, size=12, bold=False, align="left"):
        p = doc.add_paragraph()
        run = p.add_run(text.strip())
        run.font.size = Pt(size)
        run.bold = bold
        p.paragraph_format.line_spacing = 1.5
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Title Page
    add_paragraph(book_data['title'], size=18, bold=True, align="center")
    add_paragraph(f"Grade: {book_data['grade']}", align="center")
    add_paragraph(f"Author: {book_data['author']}", align="center")
    add_paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", align="center")
    doc.add_page_break()

    # Preface
    add_paragraph("Preface", size=12, bold=True, align="center")
    add_paragraph(book_data['preface'])
    doc.add_page_break()

    # TOC
    add_paragraph("Table of Contents", size=12, bold=True, align="center")
    for line in book_data['toc']:
        add_paragraph(line)
    doc.add_page_break()

    # Chapters
    for num in sorted(book_data['chapters'].keys()):
        add_paragraph(f"{book_data['toc'][num-1]}", size=12, bold=True, align="center")
        for line in book_data['chapters'][num].split('\n'):
            if any(keyword in line.lower() for keyword in ["student learning outcomes", "activities", "assessment", "glossary"]):
                add_paragraph(line, size=12, bold=True)
            else:
                add_paragraph(line)
        doc.add_page_break()

    file_path = "/tmp/Textbook_AI.docx"
    doc.save(file_path)
    return file_path

# Export to PDF
def export_book_pdf():
    file_path = "/tmp/Textbook_AI.pdf"
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('Normal', fontName='Times-Roman', fontSize=12, leading=18)
    heading = ParagraphStyle('Heading', fontName='Times-Bold', fontSize=14, leading=18, alignment=1)

    story = []
    story.append(Paragraph(book_data['title'], ParagraphStyle('Title', fontName='Times-Bold', fontSize=18, alignment=1)))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Grade: {book_data['grade']}<br/>Author: {book_data['author']}<br/>{datetime.now().strftime('%B %d, %Y')}", normal))
    story.append(Spacer(1, 40))

    story.append(Paragraph("Preface", heading))
    story.append(Paragraph(book_data['preface'], normal))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Table of Contents", heading))
    for line in book_data['toc']:
        story.append(Paragraph(line, normal))
    story.append(Spacer(1, 20))

    for num in sorted(book_data['chapters'].keys()):
        story.append(Paragraph(book_data['toc'][num-1], heading))
        for line in book_data['chapters'][num].split('\n'):
            story.append(Paragraph(line, normal))
        story.append(Spacer(1, 20))

    doc = SimpleDocTemplate(file_path, pagesize=A4)
    doc.build(story)
    return file_path

# Gradio Interface
with gr.Blocks() as demo:
    # Developer name top center
    gr.Markdown("<h2 style='text-align: center;'>📘 AI Textbook Generator – APA Style</h2>", elem_id="title")
    gr.Markdown("<h3 style='text-align: center;'>Developed by: Najaf Ali Sharqi</h3>", elem_id="developer")

    with gr.Row():
        title = gr.Textbox(label="Book Title")
        grade = gr.Textbox(label="Grade Level")
        author = gr.Textbox(label="Author Name")
        medium = gr.Radio(choices=["English", "Urdu"], value="English", label="Medium")

    generate_structure = gr.Button("🧠 Generate TOC + Preface")
    structure_output = gr.Textbox(label="Generated Preface and TOC", lines=15)

    generate_structure.click(fn=generate_book_intro, inputs=[title, grade, author, medium], outputs=structure_output)

    gr.Markdown("### 📥 Generate Chapters One by One")
    chapter_output = gr.Textbox(label="Generated Chapter Content", lines=25)

    with gr.Row():
        for i in range(1, 8):
            gr.Button(f"Generate Chapter {i}").click(fn=generate_chapter, inputs=gr.Number(value=i, visible=False), outputs=chapter_output)

    gr.Markdown("### 💾 Download Complete Textbook")
    with gr.Row():
        download_word = gr.Button("Download MS Word")
        download_pdf = gr.Button("Download PDF")
    download_file = gr.File()

    download_word.click(fn=export_book_word, outputs=download_file)
    download_pdf.click(fn=export_book_pdf, outputs=download_file)

    gr.Markdown("<p style='text-align: center;'>Created with ❤️ using Gradio + Groq | APA 7th Edition | Pakistan Context</p>")

demo.launch()
