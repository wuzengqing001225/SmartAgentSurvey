from docx import Document
import pymupdf

try:
    import win32com.client as win32  # for .doc files on Windows
except ImportError:
    win32 = None  # Only available on Windows

def clean_text(text_list):
    """Remove unnecessary newlines and empty strings from a list of text elements."""
    cleaned_text = []
    for line in text_list:
        if line.strip():
            cleaned_text.append(line.strip())
    return cleaned_text

def extract_table_content(table):
    """Extract content from a table in a structured format."""
    table_content = []
    
    headers = []
    for cell in table.rows[0].cells:
        if cell.text.strip():
            headers.append(cell.text.strip())
    
    if len(headers) > 1:
        table_content.append("TABLE START")
        table_content.append("\t".join(headers))
        
        for row_idx in range(1, len(table.rows)):
            row_data = []
            for cell in table.rows[row_idx].cells:
                cell_text = cell.text.strip()
                row_data.append(cell_text if cell_text else "_")
            table_content.append("\t".join(row_data))
        table_content.append("TABLE END")
    else:
        for row in table.rows:
            cell_text = row.cells[0].text.strip()
            if cell_text:
                table_content.append(cell_text)
    
    return table_content

def read_word_file(word_path):
    doc = Document(word_path)
    text = []
    
    for element in doc.element.body:
        if element.tag.endswith('p'):
            paragraph = element.xpath('.//w:t')
            if paragraph:
                text_content = ''.join(p.text for p in paragraph if p.text)
                if text_content.strip():
                    text.append(text_content.strip())
        
        elif element.tag.endswith('tbl'):
            table = None
            for idx, tbl in enumerate(doc.tables):
                if tbl._element == element:
                    table = tbl
                    break
            
            if table:
                table_content = extract_table_content(table)
                text.extend(table_content)
    
    text = clean_text(text)
    return '\n'.join(text)

def read_old_word_file(doc_path):
    if not win32:
        raise EnvironmentError("win32com.client is required for .doc files and is only available on Windows.")
    
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(doc_path)
    
    text = []
    range = doc.Content
    
    for i in range(1, doc.Paragraphs.Count + 1):
        para = doc.Paragraphs(i)
        if para.Range.Tables.Count == 0:
            content = para.Range.Text.strip()
            if content:
                text.append(content)
        else:
            table = para.Range.Tables(1)
            text.append("TABLE START")
            
            headers = []
            for col in range(1, table.Columns.Count + 1):
                header = table.Cell(1, col).Range.Text.strip()
                if header:
                    headers.append(header)
            
            if headers:
                text.append("\t".join(headers))
            
            for row in range(2, table.Rows.Count + 1):
                row_data = []
                for col in range(1, table.Columns.Count + 1):
                    cell_text = table.Cell(row, col).Range.Text.strip()
                    row_data.append(cell_text if cell_text else '')
                text.append("\t".join(row_data))
            
            text.append("TABLE END")
    
    doc.Close()
    word.Quit()
    
    return "\n".join(clean_text(text))

def read_pdf_file(pdf_path):
    pdf_text = []
    with pymupdf.open(pdf_path) as pdf:
        for page in pdf:
            pdf_text.append(page.get_text())
    return "\n".join(clean_text(pdf_text)).encode('utf-8').decode('utf-8')

def read_txt_file(txt_path):
    with open(txt_path, 'r', encoding='utf-8') as file:
        return "\n".join(clean_text(file.readlines()))

def read_md_file(md_path):
    with open(md_path, 'r', encoding='utf-8') as file:
        return "\n".join(clean_text(file.readlines()))

def read_file(file_path):
    if file_path.endswith('.docx'):
        return read_word_file(file_path)
    elif file_path.endswith('.doc'):
        return read_old_word_file(file_path)
    elif file_path.endswith('.pdf'):
        return read_pdf_file(file_path)
    elif file_path.endswith('.txt'):
        return read_txt_file(file_path)
    elif file_path.endswith('.md'):
        return read_md_file(file_path)
    else:
        raise ValueError("Unsupported file format")
