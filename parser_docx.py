from docx import Document


def parse_docx(file):
    doc = Document(file)
    texts = []

    for paragraph in doc.paragraphs:
        texts.append(paragraph.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                texts.append(cell.text)

    return texts
