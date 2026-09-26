#!/usr/bin/env python3
"""Render the entire diagnosis into a single paginated PDF, without truncation."""
import html
from report_language import labels_for, language_of, metadata_label, canonical_code
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

WIDTH, HEIGHT = 960, 540
MARGIN = 46
INK = colors.HexColor('#15334D')
MUTED = colors.HexColor('#536E82')
BLUE = colors.HexColor('#427AA3')
PALE = colors.HexColor('#E7F2FA')
BG = colors.HexColor('#F8FBFE')
FONT = 'KKChinese'


def label_time(value: float) -> str:
    milliseconds = round(float(value) * 1000)
    minutes, rest = divmod(milliseconds, 60000)
    seconds, ms = divmod(rest, 1000)
    return f'{minutes:02d}:{seconds:02d}' + (f'.{ms:03d}' if ms else '')


def extract_body_text(reader, plan):
    """Exclude our page chrome so a paragraph can span pages during validation."""
    labels = labels_for(plan)
    bodies = []
    for index, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ''
        prefix = f"{labels['report']}\n{labels['footer']}\n{index}\n"
        if not text.startswith(prefix):
            raise ValueError(f'Unexpected PDF text order on page {index}; verify the rendered report.')
        bodies.append(text[len(prefix):])
    return '\n'.join(bodies)


def body_fields(plan: dict):
    """All user-facing semantic text; reused by the completeness verifier."""
    yield plan.get('title', labels_for(plan)['title'])
    yield plan.get('one_line_judgment', '')
    yield plan['creator_intent']['summary']
    for strength in plan.get('strengths', []):
        yield strength['headline']
        yield strength['evidence']
    for issue in plan['issues']:
        for key in ('headline', 'evidence', 'action'):
            yield issue[key]
        for moment in issue['evidence_moments']:
            yield moment['label']
        method = issue['kk_method']
        for key in ('name', 'rule', 'why_here'):
            yield method[key]
        yield from method['case_ids']
        yield method.get('reference_note', '')
    yield from plan['quick_actions']
    yield plan.get('next_practice', '')
    yield from plan.get('evidence_limits', [])
    for item in plan['further_learning']:
        for key in ('source_type', 'reference_level', 'source_id', 'title', 'focus',
                    'user_group_label', 'source_group_label'):
            value = item.get(key, '')
            yield metadata_label(value, plan) if key in ('source_type', 'reference_level') else value


class EvidenceImage(Flowable):
    """Show the full frame at its original aspect ratio, with no crop or overlay."""
    def __init__(self, path: Path, width: float, height: float = 142):
        super().__init__()
        self.path, self.width, self.height = path, width, height

    def draw(self):
        self.canv.setFillColor(PALE)
        self.canv.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)
        image = ImageReader(str(self.path))
        iw, ih = image.getSize()
        scale = min(self.width / iw, self.height / ih)
        w, h = iw * scale, ih * scale
        self.canv.drawImage(image, (self.width-w)/2, (self.height-h)/2, w, h, mask='auto')


def build(plan: dict, output: Path, frames: list[tuple[float, Path]]) -> None:
    labels = labels_for(plan)
    wrap = 'CJK' if language_of(plan) == 'zh' else None
    font = Path(__file__).resolve().parents[1] / 'assets/fonts/NotoSansSC-Regular.ttf'
    # Embed the actual bundled font; do not rely on reader-side CJK fonts.
    pdfmetrics.registerFont(TTFont(FONT, str(font)))
    styles = {
        'title': ParagraphStyle('title', fontName=FONT, fontSize=29, leading=39, textColor=INK, spaceAfter=20, wordWrap=wrap),
        'h1': ParagraphStyle('h1', fontName=FONT, fontSize=24, leading=32, textColor=INK, spaceAfter=15, wordWrap=wrap, keepWithNext=True),
        'h2': ParagraphStyle('h2', fontName=FONT, fontSize=14, leading=21, textColor=BLUE, spaceBefore=12, spaceAfter=6, wordWrap=wrap, keepWithNext=True),
        'body': ParagraphStyle('body', fontName=FONT, fontSize=12.5, leading=19, textColor=INK, spaceAfter=9, wordWrap=wrap, splitLongWords=True),
        'small': ParagraphStyle('small', fontName=FONT, fontSize=10, leading=15, textColor=MUTED, spaceAfter=7, wordWrap=wrap),
        'lead': ParagraphStyle('lead', fontName=FONT, fontSize=18, leading=28, textColor=BLUE, spaceAfter=18, wordWrap=wrap),
    }
    story = []

    def p(text, style='body'):
        return Paragraph(html.escape(str(text)).replace('\n', '<br/>'), styles[style])

    def section(title, text):
        story.extend([p(title, 'h2'), p(text)])

    def frame_at(time):
        pair = min(frames, key=lambda item: abs(item[0] - float(time)))
        if abs(pair[0] - float(time)) > 0.0005:
            raise ValueError(f'未取得 {time}s 对应的原片截图。')
        return pair[1]

    def frame_grid(moments):
        rows = []
        cell_width = (WIDTH - 2 * MARGIN - 24) / 2
        for index in range(0, len(moments), 2):
            cells = []
            for moment in moments[index:index+2]:
                cells.append([EvidenceImage(frame_at(moment['time']), cell_width), Spacer(1, 6),
                              p(f"{label_time(moment['time'])} | {moment['label']}", 'small')])
            if len(cells) == 1:
                cells.append('')
            table = Table([cells], colWidths=[cell_width+12, cell_width+12])
            table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'),
                                       ('LEFTPADDING', (0,0), (-1,-1), 0),
                                       ('RIGHTPADDING', (0,0), (-1,-1), 12),
                                       ('TOPPADDING', (0,0), (-1,-1), 0),
                                       ('BOTTOMPADDING', (0,0), (-1,-1), 5)]))
            rows.append(table)
        return rows

    def new_section(title):
        story.extend([PageBreak(), p(title, 'h1')])

    story.extend([Spacer(1, 24), p('KK / AI SHORT VIDEO REVIEW', 'small'),
                  p(plan.get('title', labels['title']), 'title'),
                  p(plan.get('one_line_judgment', labels['tagline']), 'lead')])
    section(labels['intent'], plan['creator_intent']['summary'])
    story.extend([p(labels['intent_confidence'] + labels[plan['creator_intent']['confidence']], 'small'),
                  Spacer(1, 20), p(labels['cover_note'], 'small')])

    strengths = plan.get('strengths', [])
    if strengths:
        new_section(labels['strengths'])
        story.extend(frame_grid([{'time': item['start'], 'label': item['headline']} for item in strengths]))
        for index, strength in enumerate(strengths, 1):
            section(f"{index}. {strength['headline']}", strength['evidence'])

    for index, issue in enumerate(plan['issues'], 1):
        new_section(f"{labels['issue']} {index} / {issue['headline']}")
        story.append(p(f"{label_time(issue['start'])} - {label_time(issue['end'])}  |  {labels['confidence']}{labels[issue['confidence']]}", 'small'))
        story.extend(frame_grid(issue['evidence_moments']))
        section(labels['evidence'], issue['evidence'])
        section(labels['action'], issue['action'])
        method = issue['kk_method']
        section(labels['method'] + method['name'], method['rule'])
        source_note = labels['separator'].join(map(str, method['case_ids']))
        if method.get('reference_note'):
            source_note += (labels['note_separator'] if source_note else '') + method['reference_note']
        section(labels['why'], method['why_here'] + '\n' + labels['sources'] + source_note)

    new_section(labels['actions'] if plan['issues'] else labels['next_steps'])
    if not plan['issues']:
        story.append(p(labels['no_issues']))
    for index, action in enumerate(plan['quick_actions'], 1):
        story.append(p(f'{index}. {action}'))
    if plan.get('next_practice'):
        section(labels['practice'], plan['next_practice'])
    if plan.get('evidence_limits'):
        story.append(p(labels['limits'], 'h2'))
        for item in plan['evidence_limits']:
            story.append(p(item))

    if plan['further_learning']:
        new_section(labels['learning'])
    for item in plan['further_learning']:
        story.append(p(f"{labels['related']} {item['issue_id']} | {metadata_label(item.get('reference_level', 'method_level'), plan)}", 'h2'))
        story.append(p(' | '.join(str(metadata_label(item.get(key, ''), plan) if key == 'source_type' else item.get(key, '')) for key in ('source_type', 'source_id', 'title') if item.get(key))))
        if canonical_code(item.get('reference_level')) == 'shot_group':
            for prefix, title in (('user', labels['user']), ('source', labels['source'])):
                story.append(p(f"{title} {label_time(item[prefix+'_start'])} - {label_time(item[prefix+'_end'])} | {item[prefix+'_group_label']}", 'small'))
        story.append(p(item['focus']))
    if plan['further_learning']:
        story.extend([Spacer(1, 12), p(labels['reference_note'], 'small')])

    def page_chrome(c, doc):
        c.saveState()
        c.setFillColor(BG)
        c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
        c.setFont(FONT, 10)
        c.setFillColor(BLUE)
        c.drawString(MARGIN, HEIGHT-30, labels['report'])
        c.setStrokeColor(colors.HexColor('#D6E5F0'))
        c.line(MARGIN, HEIGHT-42, WIDTH-MARGIN, HEIGHT-42)
        c.setFillColor(MUTED)
        c.setFont(FONT, 9)
        c.drawString(MARGIN, 23, labels['footer'])
        c.drawRightString(WIDTH-MARGIN, 23, f'{doc.page}')
        c.restoreState()

    doc = SimpleDocTemplate(str(output), pagesize=(WIDTH, HEIGHT), leftMargin=MARGIN,
                           rightMargin=MARGIN, topMargin=57, bottomMargin=45,
                           title=str(plan.get('title', labels['report'])),
                           author='KK', pageCompression=1)
    doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
