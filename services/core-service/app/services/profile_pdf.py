from html import escape
from io import BytesIO
from pathlib import Path
from threading import Lock
from unicodedata import normalize

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.schemas.user import ProfileResponse

FONT = "DejaVuSans"
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "DejaVuSans.ttf"
pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))
FONT_LOCK = Lock()

BODY = ParagraphStyle(
    "CVBody", fontName=FONT, fontSize=10, leading=15,
    textColor=colors.HexColor("#142B4A"), spaceAfter=6,
)
TITLE = ParagraphStyle("CVTitle", parent=BODY, fontSize=22, leading=28, keepWithNext=True)
HEADING = ParagraphStyle(
    "CVHeading", parent=BODY, fontSize=13, leading=18,
    textColor=colors.HexColor("#155EEF"), spaceBefore=10, keepWithNext=True,
)


def _paragraph(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    lines = normalize("NFC", text).splitlines()
    return Paragraph("<br/>".join(escape(line) for line in lines), style)


def render_profile_pdf(profile: ProfileResponse, skill_names: list[str]) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=45, rightMargin=45,
        topMargin=45, bottomMargin=45, title="Hồ sơ ứng viên",
    )
    contact = " | ".join(value for value in (profile.email, profile.phone, profile.location) if value)
    story = [_paragraph(profile.full_name, TITLE), _paragraph(contact)]

    if profile.summary:
        story.extend((_paragraph("Giới thiệu", HEADING), _paragraph(profile.summary)))
    if skill_names:
        story.extend((_paragraph("Kỹ năng", HEADING), _paragraph(", ".join(skill_names))))

    if profile.experience:
        story.append(_paragraph("Kinh nghiệm làm việc", HEADING))
        for item in profile.experience:
            years = item.get("years")
            details = (item.get("position"), item.get("company"), f"{years} năm" if years is not None else None)
            label = " | ".join(str(value) for value in details if value)
            if label:
                story.append(_paragraph(label))
            if item.get("description"):
                story.append(_paragraph(str(item["description"])))

    if profile.education:
        story.append(_paragraph("Học vấn", HEADING))
        for item in profile.education:
            details = (item.get("school"), item.get("major"), item.get("graduation_year"))
            label = " | ".join(str(value) for value in details if value)
            if label:
                story.append(_paragraph(label))

    # ReportLab tracks font subsets while a document is being built.
    with FONT_LOCK:
        document.build(story)
    return output.getvalue()
