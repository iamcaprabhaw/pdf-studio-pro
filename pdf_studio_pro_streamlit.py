import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile

# ---------- Page Configuration ----------
st.set_page_config(
    page_title="PDF Studio Pro",
    page_icon="📄",
    layout="centered"
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #FFD60A;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #E0E1DD;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
    }
    .success-box {
        padding: 1rem;
        background-color: #1B4332;
        border-radius: 8px;
        border-left: 4px solid #40916C;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Core PDF Operations ----------

def merge_pdfs(uploaded_files):
    """Merge multiple PDFs into one."""
    writer = PdfWriter()
    for pdf_file in uploaded_files:
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            writer.add_page(page)
    
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def _parse_segments(spec_text, total_pages):
    """
    Parse inputs like "1,3-5,7" into [(1,1), (3,5), (7,7)]
    Validates bounds against total_pages.
    """
    spec_text = spec_text.replace(" ", "")
    if not spec_text:
        raise ValueError("No ranges provided.")

    segments = []
    tokens = [t for t in spec_text.split(",") if t]
    for t in tokens:
        if "-" in t:
            a, b = t.split("-", 1)
            if not a.isdigit() or not b.isdigit():
                raise ValueError(f"Invalid range: {t}")
            start, end = int(a), int(b)
        else:
            if not t.isdigit():
                raise ValueError(f"Invalid page number: {t}")
            start = end = int(t)

        if start < 1 or end < 1 or end < start:
            raise ValueError(f"Invalid segment: {t}")
        if end > total_pages:
            raise ValueError(f"Segment {t} exceeds total pages ({total_pages}).")
        segments.append((start, end))

    return segments

def split_pdf(uploaded_file, spec_text, original_filename):
    """
    Split PDF into multiple files based on page ranges.
    Returns list of (filename, bytes) tuples.
    """
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    segments = _parse_segments(spec_text, total_pages)

    base = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    
    created_files = []
    for idx, (start, end) in enumerate(segments, 1):
        writer = PdfWriter()
        for p in range(start - 1, end):
            writer.add_page(reader.pages[p])

        if start == end:
            out_name = f"{base}_p{start}.pdf"
        else:
            out_name = f"{base}_p{start}-{end}.pdf"

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        created_files.append((out_name, output.getvalue()))

    return created_files

def extract_pages(uploaded_file, pages_text):
    """Extract specific pages from a PDF."""
    reader = PdfReader(uploaded_file)
    total = len(reader.pages)
    writer = PdfWriter()

    pages = [p.strip() for p in pages_text.split(",") if p.strip()]
    
    for p in pages:
        if not p.isdigit():
            raise ValueError(f"Invalid page number: {p}")
        p_int = int(p)
        if p_int < 1 or p_int > total:
            raise ValueError(f"Page {p_int} out of bounds (1..{total}).")
        writer.add_page(reader.pages[p_int - 1])

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

def get_pdf_info(uploaded_file):
    """Get basic info about a PDF file."""
    reader = PdfReader(uploaded_file)
    return len(reader.pages)

# ---------- UI ----------

# Title
st.markdown('<h1 class="main-title">📄 PDF Studio Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Merge • Split • Extract</p>', unsafe_allow_html=True)

# Tabs for different operations
tab1, tab2, tab3 = st.tabs(["🔗 Merge PDFs", "✂️ Split PDF", "📑 Extract Pages"])

# ---------- Merge Tab ----------
with tab1:
    st.markdown("### Merge Multiple PDFs")
    st.markdown("Upload multiple PDF files to combine them into a single document.")
    
    merge_files = st.file_uploader(
        "Select PDF files to merge",
        type="pdf",
        accept_multiple_files=True,
        key="merge_uploader"
    )
    
    if merge_files:
        st.info(f"📁 {len(merge_files)} file(s) selected")
        
        # Show file order
        st.markdown("**File order (will be merged in this sequence):**")
        for i, f in enumerate(merge_files, 1):
            pages = get_pdf_info(f)
            st.write(f"{i}. {f.name} ({pages} pages)")
            f.seek(0)  # Reset file pointer after reading
        
        if st.button("🔗 Merge PDFs", type="primary", key="merge_btn"):
            with st.spinner("Merging PDFs..."):
                try:
                    # Reset all file pointers
                    for f in merge_files:
                        f.seek(0)
                    
                    merged_pdf = merge_pdfs(merge_files)
                    
                    st.success("✅ PDFs merged successfully!")
                    st.download_button(
                        label="📥 Download Merged PDF",
                        data=merged_pdf,
                        file_name="merged.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# ---------- Split Tab ----------
with tab2:
    st.markdown("### Split PDF by Pages/Ranges")
    st.markdown("Split a PDF into multiple files based on page numbers or ranges.")
    
    split_file = st.file_uploader(
        "Select PDF to split",
        type="pdf",
        key="split_uploader"
    )
    
    if split_file:
        total_pages = get_pdf_info(split_file)
        split_file.seek(0)
        
        st.info(f"📄 **{split_file.name}** - {total_pages} pages")
        
        st.markdown("**Enter pages/ranges to split:**")
        split_spec = st.text_input(
            "Format: 1,3-5,7 (creates separate files for each segment)",
            value="1,3-5,7",
            key="split_spec",
            help="Example: '1,3-5,7' creates 3 files: page 1, pages 3-5, and page 7"
        )
        
        # Preview what will be created
        if split_spec:
            try:
                segments = _parse_segments(split_spec, total_pages)
                st.markdown("**Preview - Files to be created:**")
                base = split_file.name.rsplit('.', 1)[0]
                for start, end in segments:
                    if start == end:
                        st.write(f"• {base}_p{start}.pdf (page {start})")
                    else:
                        st.write(f"• {base}_p{start}-{end}.pdf (pages {start}-{end})")
            except ValueError as e:
                st.warning(f"⚠️ {str(e)}")
        
        if st.button("✂️ Split PDF", type="primary", key="split_btn"):
            with st.spinner("Splitting PDF..."):
                try:
                    split_file.seek(0)
                    created_files = split_pdf(split_file, split_spec, split_file.name)
                    
                    st.success(f"✅ Created {len(created_files)} file(s)!")
                    
                    if len(created_files) == 1:
                        # Single file - direct download
                        filename, data = created_files[0]
                        st.download_button(
                            label=f"📥 Download {filename}",
                            data=data,
                            file_name=filename,
                            mime="application/pdf"
                        )
                    else:
                        # Multiple files - create ZIP
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                            for filename, data in created_files:
                                zf.writestr(filename, data)
                        zip_buffer.seek(0)
                        
                        st.download_button(
                            label="📥 Download All (ZIP)",
                            data=zip_buffer,
                            file_name="split_pdfs.zip",
                            mime="application/zip"
                        )
                        
                        # Also offer individual downloads
                        st.markdown("**Or download individually:**")
                        cols = st.columns(min(len(created_files), 3))
                        for i, (filename, data) in enumerate(created_files):
                            with cols[i % 3]:
                                st.download_button(
                                    label=f"📄 {filename}",
                                    data=data,
                                    file_name=filename,
                                    mime="application/pdf",
                                    key=f"split_download_{i}"
                                )
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# ---------- Extract Tab ----------
with tab3:
    st.markdown("### Extract Specific Pages")
    st.markdown("Extract selected pages from a PDF into a new file.")
    
    extract_file = st.file_uploader(
        "Select PDF to extract from",
        type="pdf",
        key="extract_uploader"
    )
    
    if extract_file:
        total_pages = get_pdf_info(extract_file)
        extract_file.seek(0)
        
        st.info(f"📄 **{extract_file.name}** - {total_pages} pages")
        
        st.markdown("**Enter page numbers to extract:**")
        extract_pages_input = st.text_input(
            "Format: 1,3,5,7 (comma-separated page numbers)",
            placeholder="e.g., 1,3,5,7",
            key="extract_pages",
            help="Enter page numbers separated by commas. Pages will appear in the order specified."
        )
        
        if extract_pages_input:
            # Show preview
            pages_list = [p.strip() for p in extract_pages_input.split(",") if p.strip()]
            if pages_list:
                st.markdown(f"**Will extract {len(pages_list)} page(s):** {', '.join(pages_list)}")
        
        if st.button("📑 Extract Pages", type="primary", key="extract_btn"):
            if not extract_pages_input or not extract_pages_input.strip():
                st.error("❌ Please enter at least one page number.")
            else:
                with st.spinner("Extracting pages..."):
                    try:
                        extract_file.seek(0)
                        extracted_pdf = extract_pages(extract_file, extract_pages_input)
                        
                        st.success("✅ Pages extracted successfully!")
                        st.download_button(
                            label="📥 Download Extracted PDF",
                            data=extracted_pdf,
                            file_name="extracted.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #778DA9; font-size: 0.85rem;'>"
    "PDF Studio Pro • Built with Streamlit"
    "</p>",
    unsafe_allow_html=True
)
