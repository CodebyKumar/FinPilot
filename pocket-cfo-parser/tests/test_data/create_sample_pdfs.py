import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_hdfc_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], alignment=1)
    
    # Header
    elements.append(Paragraph("HDFC Bank — Account Statement", header_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Account Number: XX1234", styles['Normal']))
    elements.append(Paragraph("Period: April 2026", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [
        ['Date', 'Description', 'Debit (₹)', 'Credit (₹)', 'Balance (₹)'],
        ['01-Apr-26', 'Opening Balance', '', '', '50000.00'],
        ['02-Apr-26', 'Swiggy Order', '450.00', '', '49550.00'],
        ['05-Apr-26', 'Salary credit from Infosys Ltd', '', '85000.00', '134550.00'],
        ['08-Apr-26', 'Rent payment', '25000.00', '', '109550.00'],
        ['10-Apr-26', 'Zomato', '600.00', '', '108950.00'],
        ['12-Apr-26', 'Electricity bill', '1250.00', '', '107700.00'],
        ['15-Apr-26', 'Amazon Pay', '3400.00', '', '104300.00'],
        ['18-Apr-26', 'UPI transfer to Rahul Kumar', '5000.00', '', '99300.00'],
        ['20-Apr-26', 'ATM withdrawal', '2000.00', '', '97300.00'],
    ]
    
    table = Table(data, colWidths=[70, 200, 70, 70, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)


def create_sbi_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Heading1'], alignment=1)
    
    # Header
    elements.append(Paragraph("State Bank of India — Account Statement", header_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Account Number: XXXXXX5678", styles['Normal']))
    elements.append(Paragraph("Period: April 2026", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Table Data
    data = [
        ['Date', 'Description', 'Debit (₹)', 'Credit (₹)', 'Balance (₹)'],
        ['01-Apr-26', 'Opening Balance', '', '', '20000.00'],
        ['03-Apr-26', 'UPI/6105432/Grocery Store/UPI', '1500.00', '', '18500.00'],
        ['05-Apr-26', 'UPI/6105890/Medical Store/UPI', '850.50', '', '17649.50'],
        ['10-Apr-26', 'REV/School Fees/Credit', '', '5000.00', '22649.50'],
        ['11-Apr-26', 'NFET/Salary/TCS', '', '65000.00', '87649.50'],
        ['14-Apr-26', 'UPI/6105555/Mobile Recharge', '299.00', '', '87350.50'],
        ['18-Apr-26', 'ACH/Mutual Fund/SIP', '5000.00', '', '82350.50'],
    ]
    
    table = Table(data, colWidths=[70, 200, 70, 70, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightsteelblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    hdfc_path = os.path.join(base_dir, "hdfc_statement.pdf")
    sbi_path = os.path.join(base_dir, "sbi_statement.pdf")
    
    create_hdfc_pdf(hdfc_path)
    create_sbi_pdf(sbi_path)
    
    print(f"Created: {hdfc_path}")
    print(f"Created: {sbi_path}")
