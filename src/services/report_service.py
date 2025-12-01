from fpdf import FPDF
import pandas as pd
import streamlit as st

class PDF(FPDF):
    def header(self): 
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'Hajri.ai - Attendance Report', 0, 1, 'C')
        self.ln(10)
    
    def footer(self): 
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

class ReportService:
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_pdf_report(subject_name: str, metrics: dict, full_report_df: pd.DataFrame) -> bytes:
        pdf = PDF()
        pdf.add_page(orientation='L')
        pdf.set_font('Helvetica', '', 12)
        
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, f"Summary: {subject_name}", 0, 1, 'L')
        pdf.set_font('Helvetica', '', 12)
        
        pdf.cell(0, 8, f"  Students: {metrics['total_students']}", 0, 1, 'L')
        pdf.cell(0, 8, f"  Lectures: {metrics['total_lectures']}", 0, 1, 'L')
        pdf.cell(0, 8, f"  Overall Attendance: {metrics['overall_attendance']:.2f}%", 0, 1, 'L')
        pdf.ln(10)
        
        pdf.set_font('Helvetica', 'B', 10)
        
        display_cols = ['name', 'username'] + [col for col in full_report_df.columns if col not in ['user_id', 'username', 'name', 'email', 'Total', 'Percentage']] + ['Percentage']
        report_table_df = full_report_df[display_cols].rename(columns={"name": "Name", "username": "Enrollment"})
        
        page_width = pdf.w - 2 * pdf.l_margin
        base_col_width = page_width * 0.15
        percent_col_width = page_width * 0.10
        
        num_lecture_cols = len(display_cols) - 3
        lecture_col_width = (page_width - (2 * base_col_width) - percent_col_width) / num_lecture_cols if num_lecture_cols > 0 else 0
        lecture_col_width = min(lecture_col_width, 30)
        
        col_widths = [base_col_width, base_col_width] + [lecture_col_width] * num_lecture_cols + [percent_col_width]
        
        for i, header in enumerate(report_table_df.columns): 
            display_header = (str(header)[:8] + '..') if len(str(header)) > 10 else str(header)
            pdf.cell(col_widths[i], 10, display_header, 1, 0, 'C')
        pdf.ln()
        
        pdf.set_font('Helvetica', '', 9)
        for _, row in report_table_df.iterrows():
            for i, item in enumerate(row): 
                display_item = f"{item:.1f}%" if isinstance(item, float) else str(item)
                pdf.cell(col_widths[i], 10, display_item, 1, 0, 'C')
            pdf.ln()
            
        return bytes(pdf.output(dest='S'))
