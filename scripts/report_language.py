"""Report labels and stable metadata codes; prose is written by the Agent."""

LABELS = {
    'zh': {
        'filename': 'KK-AI短片诊断报告.pdf',
        'report': 'KK·AI短片诊断报告', 'title': '作品诊断',
        'tagline': '根据真实作品证据，找到最值得先改的地方。',
        'intent': '创作意图', 'intent_confidence': '意图置信度：',
        'cover_note': '原片证据 · 方法依据 · 修改建议',
        'strengths': '这些部分，值得保留', 'issue': '问题',
        'confidence': '判断置信度：', 'evidence': '原片证据与观看影响',
        'action': '第一轮怎么改', 'method': 'KK 方法 / ',
        'why': '为什么适用于这段作品', 'sources': '方法依据：',
        'actions': '第一轮，按这个顺序修改',
        'next_steps': '保留有效表达 / 下一步建议',
        'no_issues': '本轮未列出需要修改的明确问题。判断仅适用于本次已观察到的证据范围。',
        'practice': '下一条作品，只练一个判断', 'limits': '本次证据限制',
        'learning': '延伸学习 / 从修改中学会判断', 'related': '对应',
        'user': '本片', 'source': '参考作品',
        'reference_note': '案例提供方法依据；本次结论仍以你的原片证据为准。',
        'footer': 'AI时代，持续学习，无限进步',
        'high': '高', 'medium': '中', 'low': '低',
        'daily_shot': '每日一镜', 'long_form_tutorial': '长拉片教程',
        'unmatched': '暂未匹配直接案例', 'method_level': '方法级',
        'shot_group': '镜头组级', 'separator': '、', 'note_separator': '；',
    },
    'en': {
        'filename': 'KK-AI-Video-Diagnosis-Report.pdf',
        'report': 'KK / AI Video Diagnosis Report', 'title': 'Video Diagnosis',
        'tagline': 'Find the most useful next edit, grounded in your footage.',
        'intent': 'Creative intent', 'intent_confidence': 'Intent confidence: ',
        'cover_note': 'Source evidence / Review methods / Actionable edits',
        'strengths': 'What works well', 'issue': 'Issue',
        'confidence': 'Confidence: ', 'evidence': 'Evidence and viewing impact',
        'action': 'What to change first', 'method': 'KK method / ',
        'why': 'Why this method applies', 'sources': 'Method references: ',
        'actions': 'First revision / Order of edits',
        'next_steps': 'Keep what works / Next steps',
        'no_issues': 'No clear issue requiring a change was identified within the evidence reviewed.',
        'practice': 'One focus for your next video', 'limits': 'Evidence limitations',
        'learning': 'Further learning / Build your editing judgment', 'related': 'Related to',
        'user': 'Your video', 'source': 'Reference video',
        'reference_note': 'Cases explain the method; conclusions about your video rely on its own evidence.',
        'footer': 'In the AI era, keep learning. Keep improving.',
        'high': 'High', 'medium': 'Medium', 'low': 'Low',
        'daily_shot': 'Daily shot study', 'long_form_tutorial': 'Long-form breakdown',
        'unmatched': 'No direct case matched', 'method_level': 'Method level',
        'shot_group': 'Shot-group level', 'separator': ', ', 'note_separator': '; ',
    },
}

SOURCE_TYPES = {'daily_shot', 'long_form_tutorial', 'unmatched'}
REFERENCE_LEVELS = {'method_level', 'shot_group'}
LEGACY_CODES = {
    '每日一镜': 'daily_shot', '长拉片教程': 'long_form_tutorial',
    '暂未匹配直接案例': 'unmatched', '方法级': 'method_level', '镜头组级': 'shot_group',
}


def language_of(plan):
    language = plan.get('language', 'zh')
    if not isinstance(language, str) or language not in LABELS:
        raise ValueError('language must be zh or en; omit it for legacy Chinese plans.')
    return language


def labels_for(plan):
    return LABELS[language_of(plan)]


def canonical_code(value):
    return LEGACY_CODES.get(value, value)


def metadata_label(value, plan):
    code = canonical_code(value)
    return labels_for(plan).get(code, value)


def report_filename(plan):
    return labels_for(plan)['filename']
