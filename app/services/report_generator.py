import io
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


class ReportService:
    @staticmethod
    def generate_result_pdf(result):
        """
        Generates a professional PDF report for a single examination result.
        Returns a BytesIO stream.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor('#1a365d')  # Deep navy blue
        )

        subtitle_style = ParagraphStyle(
            'HeaderSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#4a5568')
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#2b6cb0'),
            spaceBefore=12,
            spaceAfter=6
        )

        normal_bold = ParagraphStyle(
            'NormalBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2d3748')
        )

        normal_val = ParagraphStyle(
            'NormalVal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#1a202c')
        )

        story = []

        # Header Banner
        story.append(Paragraph("CloudExam – Examination Report", title_style))
        story.append(Paragraph("Official Performance & Result Assessment Document", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2b6cb0'), spaceAfter=15))

        # Candidate Details Table
        story.append(Paragraph("Student & Examination Details", section_heading))
        student = result.student
        exam = result.exam
        attempt = result.attempt

        submission_str = attempt.submission_time.strftime('%Y-%m-%d %H:%M:%S UTC') if attempt and attempt.submission_time else result.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        start_str = attempt.start_time.strftime('%Y-%m-%d %H:%M:%S UTC') if attempt and attempt.start_time else 'N/A'
        duration_taken = f"{round((attempt.submission_time - attempt.start_time).total_seconds() / 60, 1)} minutes" if attempt and attempt.submission_time else 'N/A'

        details_data = [
            [Paragraph("Candidate Name:", normal_bold), Paragraph(student.name, normal_val),
             Paragraph("Student Email:", normal_bold), Paragraph(student.email, normal_val)],
            [Paragraph("Examination Title:", normal_bold), Paragraph(exam.title, normal_val),
             Paragraph("Subject:", normal_bold), Paragraph(exam.subject, normal_val)],
            [Paragraph("Exam Start Time:", normal_bold), Paragraph(start_str, normal_val),
             Paragraph("Submission Time:", normal_bold), Paragraph(submission_str, normal_val)],
            [Paragraph("Duration Taken:", normal_bold), Paragraph(duration_taken, normal_val),
             Paragraph("Passing Required:", normal_bold), Paragraph(f"{exam.passing_percentage}%", normal_val)]
        ]

        details_table = Table(details_data, colWidths=[110, 150, 110, 150])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 15))

        # Count answer stats
        answers = attempt.answers if attempt else []
        correct_count = sum(1 for a in answers if a.is_correct)
        unanswered_count = sum(1 for a in answers if not a.selected_answer or not a.selected_answer.strip())
        incorrect_count = max(0, len(exam.questions) - correct_count - unanswered_count)

        # Performance Summary Table
        story.append(Paragraph("Performance Summary", section_heading))

        status_color = colors.HexColor('#22543d') if result.result_status == 'PASS' else colors.HexColor('#742a2a')
        status_bg = colors.HexColor('#c6f6d5') if result.result_status == 'PASS' else colors.HexColor('#fed7d7')

        status_cell = Paragraph(
            f"<font color='{status_color.hexval()}'><b>{result.result_status}</b></font>",
            normal_bold
        )

        perf_data = [
            [Paragraph("Metric", normal_bold), Paragraph("Value", normal_bold)],
            [Paragraph("Total Questions", normal_val), Paragraph(str(len(exam.questions)), normal_val)],
            [Paragraph("Correct Answers", normal_val), Paragraph(str(correct_count), normal_val)],
            [Paragraph("Incorrect Answers", normal_val), Paragraph(str(incorrect_count), normal_val)],
            [Paragraph("Unanswered Questions", normal_val), Paragraph(str(unanswered_count), normal_val)],
            [Paragraph("Total Marks Available", normal_val), Paragraph(f"{result.total_marks:.1f}", normal_val)],
            [Paragraph("Marks Obtained", normal_val), Paragraph(f"<b>{result.obtained_marks:.1f}</b>", normal_val)],
            [Paragraph("Percentage Score", normal_val), Paragraph(f"<b>{result.percentage:.2f}%</b>", normal_val)],
            [Paragraph("Final Outcome", normal_bold), status_cell]
        ]

        perf_table = Table(perf_data, colWidths=[260, 260])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f7fafc')]),
            ('BACKGROUND', (0, -1), (-1, -1), status_bg),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(perf_table)
        story.append(Spacer(1, 20))

        # Footer Note
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=10))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#a0aec0'),
            alignment=1  # Centered
        )
        story.append(Paragraph("This is a computer-generated report issued by CloudExam Online Examination Management System.", footer_style))
        story.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", footer_style))

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_results_csv(results):
        """
        Exports a list of Result models to a CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'Result ID',
            'Student ID',
            'Student Name',
            'Student Email',
            'Exam ID',
            'Exam Title',
            'Subject',
            'Total Marks',
            'Obtained Marks',
            'Percentage',
            'Status',
            'Start Time',
            'Submission Time',
            'Date Created'
        ])

        for r in results:
            attempt = r.attempt
            start_time = attempt.start_time.strftime('%Y-%m-%d %H:%M:%S') if attempt and attempt.start_time else ''
            sub_time = attempt.submission_time.strftime('%Y-%m-%d %H:%M:%S') if attempt and attempt.submission_time else ''
            created = r.created_at.strftime('%Y-%m-%d %H:%M:%S')

            writer.writerow([
                r.id,
                r.student.id,
                r.student.name,
                r.student.email,
                r.exam.id,
                r.exam.title,
                r.exam.subject,
                r.total_marks,
                r.obtained_marks,
                r.percentage,
                r.result_status,
                start_time,
                sub_time,
                created
            ])

        return output.getvalue()
