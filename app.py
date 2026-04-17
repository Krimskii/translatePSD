import io
import tempfile

import pandas as pd
import streamlit as st

from normalizer import normalize_df
from parser_pdf import parse_pdf
from translator_hybrid import translate_df
from validator import validate_df
from writer_dxf_blocks import write_translated_dxf


st.title("AI локализатор ПСД Казахстан")

uploaded_file = st.file_uploader("Загрузить файл (Excel / PDF / DXF)")

if uploaded_file is not None:
    filename = uploaded_file.name.lower()

    if st.session_state.get("source_name") != uploaded_file.name:
        st.session_state.pop("df", None)
        st.session_state["source_name"] = uploaded_file.name

    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    elif filename.endswith(".pdf"):
        df = parse_pdf(uploaded_file)
    elif filename.endswith(".dxf"):
        import ezdxf
        from parser_dxf_block import extract_texts

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        doc = ezdxf.readfile(tmp_path)
        texts = extract_texts(doc)
        df = pd.DataFrame(texts, columns=["handle", "text"])
    else:
        st.error("Поддерживаются Excel / PDF / DXF")
        st.stop()

    if "df" not in st.session_state:
        st.session_state.df = df.copy()

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

    buffer = io.BytesIO()
    st.session_state.df.to_excel(buffer, index=False)

    st.download_button(
        label="Скачать Excel",
        data=buffer.getvalue(),
        file_name="result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if filename.endswith(".dxf") and st.button("Скачать DXF"):
        output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
        write_translated_dxf(tmp_path, output.name, st.session_state.df)

        with open(output.name, "rb") as file:
            st.download_button(
                "Скачать переведенный DXF",
                file.read(),
                file_name="translated.dxf",
            )
