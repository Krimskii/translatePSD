import streamlit as st
import pandas as pd
import io
import tempfile

from translator_hybrid import translate_df
from normalizer import normalize_df
from validator import validate_df
from parser_pdf import parse_pdf
from writer_dxf import write_translated_dxf
from writer_dxf_blocks import write_translated_dxf

st.title("AI локализатор ПСД Казахстан")

file = st.file_uploader("Загрузить файл (Excel / PDF / DXF)")

if file is not None:

    filename = file.name.lower()

    # -------- Excel --------
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(file)

    # -------- PDF --------
    elif filename.endswith(".pdf"):
        df = parse_pdf(file)

    # -------- DXF --------
    elif filename.endswith(".dxf"):

        from parser_dxf_block import extract_texts
        import ezdxf

        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        doc = ezdxf.readfile(tmp_path)

        texts = extract_texts(doc)

        df = pd.DataFrame(texts, columns=["handle", "text"])

    else:
        st.error("Поддерживаются Excel / PDF / DXF")
        st.stop()

    # сохраняем исходный df один раз
    if "df" not in st.session_state:
        st.session_state.df = df

    # -------- ПЕРЕВОД --------
    if st.button("Перевести"):
        with st.spinner("Перевод..."):
            st.session_state.df = translate_df(st.session_state.df)

    # -------- НОРМАЛИЗАЦИЯ --------
    if st.button("Нормализовать РК"):
        with st.spinner("Нормализация..."):
            st.session_state.df = normalize_df(st.session_state.df)

    # -------- ПРОВЕРКА --------
    if st.button("Проверить СН РК"):
        report = validate_df(st.session_state.df)
        st.dataframe(report)

    # -------- ПРЕДПРОСМОТР --------
    st.dataframe(st.session_state.df)

    # -------- СКАЧАТЬ --------
    buffer = io.BytesIO()
    st.session_state.df.to_excel(buffer, index=False)

    st.download_button(
        label="Скачать",
        data=buffer.getvalue(),
        file_name="result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ---------- DXF EXPORT ----------
    if filename.endswith(".dxf"):

        if st.button("Скачать DXF"):

            output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")

            write_translated_dxf(
                tmp_path,
                output.name,
                st.session_state.df
            )

            with open(output.name, "rb") as f:

                st.download_button(
                    "Скачать переведенный DXF",
                    f,
                    file_name="translated.dxf"
                )