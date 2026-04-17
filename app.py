import io
import tempfile

import pandas as pd
import streamlit as st

from batch_processing import build_batch_zip, process_uploaded_file
from normative_dictionary import (
    DEFAULT_PATH as NORMATIVE_DICTIONARY_PATH,
    get_recommended_candidates,
    promote_recommended_candidates,
)
from normalizer import normalize_df
from output_names import build_ru_name
from parser_docx import parse_docx
from parser_pdf import parse_pdf
from translator_hybrid import translate_df
from translate_docx import apply_docx_dataframe
from translate_excel import apply_excel_dataframe, workbook_to_translation_df
from translate_pdf import apply_pdf_dataframe
from validator import validate_df
from writer_dxf_blocks import write_translated_dxf


st.title("AI локализатор ПСД Казахстан")
st.caption(
    f"Нормативный словарь РК: `{NORMATIVE_DICTIONARY_PATH}`. "
    "Лист `approved_terms` хранит утвержденные термины, лист `candidates` пополняется автоматически."
)
st.caption("Для CAD загружайте `DXF`. Если исходник в `DWG`, сохраните его в AutoCAD как `DXF`.")

recommended_candidates = get_recommended_candidates()
if not recommended_candidates.empty:
    st.subheader("Рекомендуемые термины")
    st.write(f"Готово к переносу в `approved_terms`: {len(recommended_candidates)}")
    st.dataframe(recommended_candidates.head(20))
    if st.button("Перенести рекомендованные в approved_terms"):
        promoted_count = promote_recommended_candidates()
        st.success(f"Перенесено в approved_terms: {promoted_count}")
        st.rerun()

uploaded_files = st.file_uploader(
    "Загрузить файл (Excel / PDF / DOCX / DXF)",
    accept_multiple_files=True,
)

if uploaded_files:
    source_names = tuple(file.name for file in uploaded_files)

    if st.session_state.get("source_names") != source_names:
        st.session_state.pop("df", None)
        st.session_state.pop("batch_results", None)
        st.session_state.pop("batch_zip", None)
        st.session_state.pop("batch_report_df", None)
        st.session_state["source_names"] = source_names

    if len(uploaded_files) > 1:
        st.subheader("Пакетная обработка")
        st.write(f"Файлов в очереди: {len(uploaded_files)}")
        run_normalize = st.checkbox("Нормализовать РК после перевода", value=True)
        run_validate = st.checkbox("Проверять СН РК после перевода", value=True)

        if st.button("Пакетно перевести"):
            results = []
            progress = st.progress(0, text="Старт пакетной обработки")

            for index, file in enumerate(uploaded_files, start=1):
                progress.progress(
                    index / len(uploaded_files),
                    text=f"Обрабатываю {index}/{len(uploaded_files)}: {file.name}",
                )
                results.append(process_uploaded_file(file, normalize=run_normalize, validate=run_validate))

            st.session_state["batch_results"] = results
            st.session_state["batch_report_df"] = pd.DataFrame(
                [
                    {
                        "file_name": result["file_name"],
                        "output_name": result["output_name"],
                        "status": result["status"],
                        "rows": result["rows"],
                        "warnings": result["warnings"],
                        "issues": result["issues"],
                    }
                    for result in results
                ]
            )
            st.session_state["batch_zip"] = build_batch_zip(results)
            progress.progress(1.0, text="Пакетная обработка завершена")

        if "batch_report_df" in st.session_state:
            st.dataframe(st.session_state["batch_report_df"])
            st.download_button(
                label="Скачать ZIP с результатами",
                data=st.session_state["batch_zip"],
                file_name="batch_results_RU.zip",
                mime="application/zip",
            )

            batch_report_buffer = io.BytesIO()
            st.session_state["batch_report_df"].to_excel(batch_report_buffer, index=False)
            st.download_button(
                label="Скачать отчет Excel",
                data=batch_report_buffer.getvalue(),
                file_name="batch_report_RU.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    else:
        uploaded_file = uploaded_files[0]
        filename = uploaded_file.name.lower()

        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = workbook_to_translation_df(uploaded_file)
        elif filename.endswith(".docx"):
            texts = parse_docx(uploaded_file)
            df = pd.DataFrame({"text": texts})
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
            st.error("Поддерживаются Excel / PDF / DOCX / DXF")
            st.stop()

        if "df" not in st.session_state:
            st.session_state.df = df.copy()

        if filename.endswith(".pdf") and st.session_state.df.empty:
            st.warning(
                "PDF не дал текстовых блоков даже после OCR. "
                "Вероятно, это сложный скан или качество страниц слишком низкое для распознавания."
            )

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
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                source_suffix = ".xls" if filename.endswith(".xls") else ".xlsx"
                with tempfile.NamedTemporaryFile(delete=False, suffix=source_suffix) as source_tmp:
                    source_tmp.write(uploaded_file.getvalue())
                    source_path = source_tmp.name

                output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                output.close()
                apply_excel_dataframe(source_path, output.name, st.session_state.df)

                with open(output.name, "rb") as file:
                    st.download_button(
                        label="Скачать Excel",
                        data=file.read(),
                        file_name=build_ru_name(uploaded_file.name, output_ext=".xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            else:
                buffer = io.BytesIO()
                st.session_state.df.to_excel(buffer, index=False)
                st.download_button(
                    label="Скачать Excel",
                    data=buffer.getvalue(),
                    file_name=build_ru_name(uploaded_file.name, output_ext=".xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except ModuleNotFoundError as exc:
            if exc.name == "openpyxl":
                st.warning("Для выгрузки в Excel нужен пакет openpyxl. Пока доступна выгрузка в CSV.")
                csv_data = st.session_state.df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="Скачать CSV",
                    data=csv_data,
                    file_name=build_ru_name(uploaded_file.name, output_ext=".csv"),
                    mime="text/csv",
                )
            else:
                raise

        if filename.endswith(".dxf") and st.button("Скачать DXF"):
            output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf")
            write_translated_dxf(tmp_path, output.name, st.session_state.df)

            with open(output.name, "rb") as file:
                st.download_button(
                    "Скачать переведенный DXF",
                    file.read(),
                    file_name=build_ru_name(uploaded_file.name, output_ext=".dxf"),
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
                    file_name=build_ru_name(uploaded_file.name, output_ext=".docx"),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

        if filename.endswith(".pdf") and st.button("Скачать PDF"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as source_tmp:
                source_tmp.write(uploaded_file.getvalue())
                source_path = source_tmp.name

            output = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            output.close()
            apply_pdf_dataframe(source_path, output.name, st.session_state.df)

            with open(output.name, "rb") as file:
                st.download_button(
                    "Скачать переведенный PDF",
                    file.read(),
                    file_name=build_ru_name(uploaded_file.name, output_ext=".pdf"),
                    mime="application/pdf",
                )
