import pandas as pd

from pdf_utils import extract_pdf_blocks

def parse_pdf(file):
    blocks = extract_pdf_blocks(file)
    return pd.DataFrame(
        [
            {
                "pdf_block_index": index,
                "page": block.page_index + 1,
                "bbox": block.bbox,
                "pdf_source": block.source,
                "text": block.text,
            }
            for index, block in enumerate(blocks)
        ]
    )
