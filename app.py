import io
import tempfile

import pandas as pd
import streamlit as st

from dwg_utils import convert_dwg_to_dxf, find_dwg_converter
from normalizer import normalize_df
from parser_docx import parse_docx
from parser_pdf import parse_pdf
from translator_hybrid import translate_df
from translate_docx import apply_docx_dataframe
from translate_pdf import translate_pdf
from validator import validate_df
from writer_dxf_blocks import write_translated_dxf


st.title("AI локализатор ПСД Казахстан")

uploaded_file = st.file_uploader("Загрузить файл (Excel / PDF / DOCX / DXF / DWG)")

if uploaded_file is not None:
    filename = uploaded_file.name.lower()

    if st.session_state.get("source_name") != uploaded_file.name:
        st.session_state.pop("df", None)
        st.session_state["source_name"] = uploaded_file.name

    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    elif filename.endswith(".docx"):
        texts = parse_docx(uploaded_file)
        df = pd.DataFrame({"text": texts})
    elif filename.endswith(".pdf"):
        df = parse_pdf(uploaded_file)
    elif filename.endswith(".dxf") or filename.endswith(".dwg"):
        import ezdxf
        from parser_dxf_block import extract_texts

        source_suffix = ".dwg" if filename.endswith(".dwg") else ".dxf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=source_suffix) as tmp:
            tmp.write(uploaded_file.read())
            source_tmp_path = tmp.name

        if filename.endswith(".dwg"):
            tmp_dxf = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
            tmp_dxf.close()
            convert_dwg_to_dxf(source_tmp_path, tmp_dxf.name)
            tmp_path = tmp_dxf.name
        else:
            tmp_path = source_tmp_path

        doc = ezdxf.readfile(tmp_path)
        texts = extract_texts(doc)
        df = pd.DataFrame(texts, columns=["handle", "text"])
    else:
        st.error("Поддерживаются Excel / PDF / DOCX / DXF / DWG")
        st.stop()

    if "df" not in st.session_state:
        st.session_state.df = df.copy()

    if filename.endswith(".dwg") and not find_dwg_converter():
        st.warning("Для работы с DWG нужен установленный ODA File Converter или dwg2dxf.")

    if st.button("Перевести"):
        with st.spinner("Перевод..."):
            st.session_state.df = translate_df(st.session_state.df.copy())

    if st.button("Нормализовать РК"):
        with st.spinner("Нормализация..."):
            st.session_state.df = normalize_df(st.session_state.df.copy())

    if st.button("Проверить СН РК"):
        report = validate_df(st.session_state.df)
        st.dataframe(report)

    st.dataframe(st.session_state.df)

    try:
        buffer = io.BytesIO()
        st.session_state.df.to_excel(buffer, index=False)
        st.download_button(
            label="Скачать Excel",
            data=buffer.getvalue(),
            file_name="result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ModuleNotFoundError as exc:
        if exc.name == "openpyxl":
            st.warning("Для выгрузки в Excel нужен пакет openpyxl. Пока доступна выгрузка в CSV.")
            csv_data = st.session_state.df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="Скачать CSV",
                data=csv_data,
                file_name="result.csv",
                mime="text/csv",
            )
        else:
            raise

    if (filename.endswith(".dxf") or filename.endswith(".dwg")) and st.button("Скачать DXF"):
        output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
        write_translated_dxf(tmp_path, output.name, st.session_state.df)

        with open(output.name, "rb") as file:
            st.download_button(
                "Скачать переведенный DXF",
                file.read(),
                file_name="translated.dxf",
            )

    if filename.endswith(".docx") and st.button("Скачать DOCX"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as source_tmp:
            source_tmp.write(uploaded_file.getvalue())
            source_path = source_tmp.name

        output = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        apply_docx_dataframe(source_path, output.name, st.session_state.df)

        with open(output.name, "rb") as file:
            st.download_button(
                "Скачать переведенный DOCX",
                file.read(),
                file_name="translated.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    if filename.endswith(".pdf") and st.button("Скачать PDF"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as source_tmp:
            source_tmp.write(uploaded_file.getvalue())
            source_path = source_tmp.name

        output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        output.close()
        translate_pdf(source_path, output.name)

        with open(output.name, "rb") as file:
            st.download_button(
                "Скачать переведенный PDF",
                file.read(),
                file_name="translated.pdf",
                mime="application/pdf",
            )
