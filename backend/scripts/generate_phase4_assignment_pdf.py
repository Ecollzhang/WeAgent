"""Generate the authentic PDF used by the fixed Education demo course."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "gift-of-the-magi-reading-writing-assignment.pdf"


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9E6E2"))
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.setFillColor(colors.HexColor("#617873"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20 * mm, 10 * mm, "WeAgent Education - High School English")
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        textColor=colors.HexColor("#173F3A"),
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    )
    kicker = ParagraphStyle(
        "Kicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D8A7E"),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#173F3A"),
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=11,
        leading=17,
        textColor=colors.HexColor("#263A36"),
        spaceAfter=3.2 * mm,
    )
    task = ParagraphStyle(
        "Task",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        leftIndent=6 * mm,
        firstLineIndent=-5 * mm,
        textColor=colors.HexColor("#263A36"),
        spaceAfter=3 * mm,
    )
    note = ParagraphStyle(
        "Note",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#526C66"),
    )

    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="The Gift of the Magi - Reading and Writing Assignment",
        author="WeAgent Education",
    )
    story = [
        Paragraph("READING - EVIDENCE - WRITING", kicker),
        Paragraph("The Gift of the Magi", title),
    ]
    meta = Table(
        [["Class", "Grade 10 English"], ["Focus", "Evidence, irony, analytical writing"], ["Scoring", "100 points overall - no sub-scores"]],
        colWidths=[32 * mm, 126 * mm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E9F4F1")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#236D64")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9DBD6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([meta, Paragraph("Reading excerpt", heading)])
    paragraphs = [
        "One dollar and eighty-seven cents. That was all. And sixty cents of it was in pennies. Pennies saved one and two at a time by bargaining with the grocer and the vegetable man and the butcher until one's cheeks burned with the silent imputation of parsimony that such close dealing implied. Three times Della counted it. One dollar and eighty-seven cents. And the next day would be Christmas.",
        "There was clearly nothing to do but flop down on the shabby little couch and howl. So Della did it. While the mistress of the home is gradually subsiding from the first stage to the second, take a look at the home. A furnished flat at $8 per week. It did not exactly beggar description, but it certainly had that word on the lookout for the mendicancy squad.",
        "Now, there were two possessions of the James Dillingham Youngs in which they both took a mighty pride. One was Jim's gold watch that had been his father's and his grandfather's. The other was Della's hair. Had the queen of Sheba lived in the flat across the airshaft, Della would have let her hair hang out the window some day to dry just to depreciate Her Majesty's jewels and gifts.",
        "For there lay The Combs - the set of combs, side and back, that Della had worshipped for long in a Broadway window. Beautiful combs, pure tortoise shell, with jewelled rims - just the shade to wear in the beautiful vanished hair. They were expensive combs, she knew, and her heart had simply craved and yearned over them without the least hope of possession.",
    ]
    story.extend(Paragraph(text, body) for text in paragraphs)
    story.extend(
        [
            Spacer(1, 2 * mm),
            Paragraph(
                "Source: O. Henry, <i>The Gift of the Magi</i>, Project Gutenberg eBook #7256. Public domain in the USA. Excerpt preserves the source wording for classroom close reading.",
                note,
            ),
            PageBreak(),
            Paragraph("EVIDENCE TO INTERPRETATION", kicker),
            Paragraph("Reading and writing tasks", title),
            Paragraph("Part A - Read closely", heading),
            Paragraph("1. What does the repeated exact amount of $1.87 reveal about Della's situation and state of mind? Cite one phrase from the excerpt.", task),
            Paragraph("2. Explain how the description of the flat changes the reader's understanding of Della's decision.", task),
            Paragraph("3. Compare Jim's watch and Della's hair. How does the parallel structure prepare the story's central irony?", task),
            Paragraph("4. The combs are described after Della has cut her hair. Explain why this order makes the moment both painful and meaningful.", task),
            Paragraph("Part B - Write from evidence", heading),
            Paragraph("Write 180-220 words in response to the statement below:", body),
            Paragraph("<b>Della and Jim are both foolish and wise.</b>", ParagraphStyle("Prompt", parent=body, fontName="Helvetica-Bold", fontSize=14, leading=20, textColor=colors.HexColor("#A45B3D"), leftIndent=8 * mm, rightIndent=8 * mm, spaceBefore=3 * mm, spaceAfter=5 * mm)),
            Paragraph("State a clear claim, integrate at least two details from the text, and explain how each detail supports your interpretation. Do not retell the plot.", task),
            Paragraph("Submission check", heading),
        ]
    )
    checklist = Table(
        [["[ ]", "I made a clear claim."], ["[ ]", "I used two traceable details."], ["[ ]", "I explained why each detail matters."], ["[ ]", "I revised one sentence for clarity."]],
        colWidths=[12 * mm, 146 * mm],
    )
    checklist.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F9F8")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D2E1DD")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E1EAE7")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend(
        [
            checklist,
            Spacer(1, 6 * mm),
            Paragraph("Your teacher will award one overall score out of 100 and provide one consolidated feedback comment.", note),
        ]
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build()
