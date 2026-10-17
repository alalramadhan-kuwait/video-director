"""Plain-language messages for the Co-Pilot Studio page (Arabic first).

The rules themselves stay where they are (actions.py, store.py); their English refusal text is unchanged, so the
history, the tests and the classic route read exactly as before. This module only explains a refusal to the owner:

  explain(reason, action, args) -> {'ar', 'en', 'fix', 'known'}
      ar / en  one or two plain sentences, no internal ids (take ids, flag ids, slot ids are counted or named)
      fix      where the problem is on the page: {'panel', 'target', 'label_ar', 'label_en'}, or {'reload': True}
      known    False when no rule matched: the page then says it could not do it and keeps the English as details

Also: blockers_ar (the paid-narration plan), why_ar (why a stage or an approval is outdated), title_ar (exceptions).
"""
from __future__ import annotations
import re

GATE_PANEL = {'G1': 'g1', 'G2': 'g2', 'G3': 'g3', 'G4': 'g4', 'G5': 'g5', 'G6': 'g6'}
GATE_AR = {'G1': 'اتجاه القصة', 'G2': 'النص والافتتاحية', 'G3': 'الصوت', 'G4': 'الأسلوب البصري', 'G5': 'الفيلم', 'G6': 'التعليق المدفوع'}
STATUS_AR = {'draft': 'مسودة', 'approved': 'موافق عليها', 'rejected': 'مرفوضة', 'superseded': 'قديمة', 'changes_requested': 'طُلب تعديلها',
             'candidate': 'بانتظار مراجعتك', 'open': 'مفتوح', 'decided': 'تقرّر'}


def line_ar(lid: str, scene=False) -> str:
    """'h' -> the hook, 'l6' -> line 6 (scene 6 on film screens), 'endcard' -> the end card."""
    lid = (lid or '').strip()
    if lid == 'h': return 'الافتتاحية'
    if lid == 'endcard': return 'الختام'
    m = re.fullmatch(r'l(\d+)', lid)
    if m: return ('المشهد ' if scene else 'السطر ') + m.group(1)
    return lid


def line_en(lid: str, scene=False) -> str:
    lid = (lid or '').strip()
    if lid == 'h': return 'the hook'
    if lid == 'endcard': return 'the end card'
    m = re.fullmatch(r'l(\d+)', lid)
    return (('scene ' if scene else 'line ') + m.group(1)) if m else lid


def _lines(s: str, scene=False, lang='ar') -> str:
    ids = [x.strip() for x in re.split(r'[,،]\s*', s or '') if x.strip()]
    f = line_ar if lang == 'ar' else line_en
    return ('، ' if lang == 'ar' else ', ').join(f(i, scene) for i in ids)


def _fix(panel=None, target=None, ar='خذني إليه', en='Take me there', **kw):
    return {'panel': panel, 'target': target, 'label_ar': ar, 'label_en': en, **kw}


# (pattern, arabic, english-without-ids, fix) — arabic/english may be callables of the match
R = []
def rule(rx, ar, en, fix=None):
    R.append((re.compile(rx, re.S), ar, en, fix))

# ---------------------------------------------------------------- general
rule(r'^only the owner can make this decision', 'هذا القرار لك وحدك.', 'Only you can make this decision.')
rule(r'^this is recorded by the Co-Pilot, not sent from the page', 'هذا يسجّله المساعد نفسه، ولا يُرسل من الصفحة.', 'The Co-Pilot records this itself; it is not sent from the page.')
rule(r'^\S+ cannot be sent from the page', 'هذا الأمر لا يُرسل من الصفحة.', 'This cannot be sent from the page.')
rule(r'^unknown action', 'أمر غير معروف.', 'Unknown action.')
rule(r'^no project ', 'المشروع غير موجود.', 'The project was not found.')
rule(r'^Auto mode is not yet implemented', 'الوضع التلقائي غير متاح بعد.', 'Auto mode is not available yet.')
rule(r'^mode must be copilot or manual', 'اختر: المساعد أو اليدوي.', 'Choose Co-Pilot or Manual.')
rule(r'^already in .+ mode', 'المشروع على هذا الوضع أصلًا.', 'The project is already in this mode.')
rule(r'^this project is in Manual mode', 'المشروع في اليدوي. ارجع للمساعد أولًا.', 'This project is in Manual. Go back to the Co-Pilot first.')
rule(r'^this project is run by the Co-Pilot', 'هذا المشروع يديره المساعد. قرّر من صفحته، أو حوّله لليدوي أولًا.', 'The Co-Pilot runs this project. Decide on its page, or switch to Manual first.')
rule(r'^this is a classic project', 'هذا مشروع من الاستوديو الكلاسيكي، والمساعد لا يغيّره.', 'This is a classic project; the Co-Pilot does not change it.')
rule(r'^duration must be', 'المدة بين 20 و180 ثانية.', 'The length must be 20–180 seconds.', _fix(None, '#n-dur', 'خذني للمدة', 'Go to the length'))
rule(r'^format must be one of', 'اختر مقاسًا من القائمة.', 'Choose a format from the list.')
rule(r'^worker must be one of', 'اختر عاملًا من القائمة.', 'Choose a worker from the list.')
rule(r'^nothing to change$', 'لا يوجد تغيير.', 'Nothing to change.')
rule(r'^op must be ', 'أمر غير معروف.', 'Unknown command.')
rule(r'^switch back to Co-Pilot mode first', 'ارجع لوضع المساعد أولًا.', 'Switch back to Co-Pilot mode first.')
rule(r'^which step to retry', 'أي خطوة تعيد؟', 'Which step should be retried?')
rule(r'^the Co-Pilot is not running', 'المساعد ليس قيد العمل الآن.', 'The Co-Pilot is not running.')
rule(r'^the Co-Pilot is already running', 'المساعد يعمل أصلًا.', 'The Co-Pilot is already running.')
rule(r'^give the AI usage budget', 'اكتب ميزانية الذكاء بالدولار (من 0 إلى 50).', 'Give the AI budget in US dollars (0–50).')
rule(r'^write why you authorize this AI usage', 'اكتب سبب السماح بهذا الاستخدام (يُحفظ في السجل).', 'Write why you allow this AI usage (kept in the history).')
rule(r'^\w+ must be a positive number', 'القيمة يجب أن تكون رقمًا موجبًا.', 'The value must be a positive number.')
rule(r'^Write the idea first', 'اكتب الفكرة أولًا.', 'Write the idea first.', _fix(None, '#n-idea', 'خذني للفكرة', 'Go to the idea'))
rule(r'^Give the video a short title', 'اكتب عنوانًا قصيرًا للفيديو.', 'Give the video a short title.', _fix(None, '#n-title', 'خذني للعنوان', 'Go to the title'))
rule(r'^Choose a brand', 'اختر العلامة.', 'Choose a brand.', _fix(None, '#n-brand', 'خذني للعلامة', 'Go to the brand'))
rule(r'^path outside the project', 'هذا الملف ليس من المشروع.', 'This file is not part of the project.')
# ---------------------------------------------------------------- script and hook
rule(r'^unknown hook', 'هذه الافتتاحية غير موجودة.', 'This hook does not exist.')
rule(r'^this hook is already the opening line', 'هذه الافتتاحية مختارة أصلًا.', 'This hook is already the opening line.')
rule(r'^no script yet', 'لا يوجد نص بعد.', 'There is no script yet.')
rule(r'^no line ', 'هذا السطر غير موجود.', 'This line does not exist.')
rule(r'^the sentence is empty', 'الجملة فارغة.', 'The sentence is empty.')
rule(r'^nothing changed', 'لم يتغيّر شيء في الجملة.', 'The sentence did not change.')
rule(r'^the opening line is the hook', 'السطر الأول هو الافتتاحية: غيّرها من قسم الافتتاحيات.', 'The first line is the hook: change it in the hooks section.')
rule(r'^script v(\d+) is already (\w+)', lambda m: f'النسخة v{m[1]} {STATUS_AR.get(m[2], m[2])} من قبل.', lambda m: f'Script v{m[1]} is already {m[2]}.')
rule(r'^the AI fact check and editor review of v(\d+) have not finished', lambda m: f'فحص الحقائق ومراجعة التحرير للنسخة v{m[1]} لم ينتهيا بعد. انتظر قليلًا.',
     lambda m: f'The fact check and editor review of v{m[1]} have not finished yet.')
rule(r'^the opening line must be the chosen hook', 'السطر الأول يجب أن يكون الافتتاحية المختارة: اختر افتتاحية.', 'The first line must be the chosen hook: choose a hook.',
     _fix('g2', '.hooks', 'خذني للافتتاحيات', 'Go to the hooks'))


def _hints(s, lang):
    out = []
    for part in [p.strip() for p in (s or '').split(';') if p.strip()]:
        m = re.match(r'(\S+): cite (.+?) or a source link', part)
        if m:
            ids = [x.strip() for x in m[2].split(',')]
            out.append(f'{line_ar(m[1])}: اذكر {" أو ".join(ids)} أو رابط مصدر' if lang == 'ar' else f'{line_en(m[1])}: cite {" or ".join(ids)} or a source link')
            continue
        m = re.match(r'(\S+): no research claim is linked to it', part)
        if m:
            out.append(f'{line_ar(m[1])}: لا يوجد ادعاء مرتبط به، فضع رابط مصدر' if lang == 'ar' else f'{line_en(m[1])}: no research claim is linked, so give a source link')
    return '؛ '.join(out) if lang == 'ar' else '; '.join(out)


rule(r'^critical fact-check result on (.+?): fix the line, or override it(?:.*?\((.*)\))?$',
     lambda m: f'تحذير حرج في {_lines(m[1])}: صحّح السطر، أو اكتب في خانة «تجاوز بدليل» دليلًا لهذا السطر وجملة تشرح لماذا التحذير غلط'
               + (f' ({_hints(m[2], "ar")}).' if m[2] else '.'),
     lambda m: f'Critical fact-check result on {_lines(m[1], lang="en")}: fix the line, or override it with evidence for that line and a sentence saying why'
               + (f' ({_hints(m[2], "en")}).' if m[2] else '.'),
     _fix('g2', '[data-ov]', 'خذني للسطر', 'Go to the line'))
rule(r'^confirm you have read the warnings on (.+)', lambda m: f'أكّد أنك قرأت التحذيرات في {_lines(m[1])}: علّم مربع «قرأت التحذير» عند كل منها.',
     lambda m: f'Confirm you read the warnings on {_lines(m[1], lang="en")}: tick “I read the warning” on each.', _fix('g2', '[data-ack]:not(:checked)', 'خذني للتحذير', 'Go to the warning'))
rule(r'^v(\d+) is already (\w+); make a new version', lambda m: f'النسخة v{m[1]} {STATUS_AR.get(m[2], m[2])} من قبل.', lambda m: f'v{m[1]} is already {m[2]}.')
rule(r'^v(\d+) was replaced by v(\d+)', lambda m: f'النسخة v{m[1]} استُبدلت بالنسخة v{m[2]}: قرّر على الأحدث.', lambda m: f'v{m[1]} was replaced by v{m[2]}: decide on the latest.', {'reload': True, 'label_ar': 'اعرض الأحدث', 'label_en': 'Show the latest'})
# ---------------------------------------------------------------- gates (shared)
rule(r'^unknown gate', 'بوابة غير معروفة.', 'Unknown gate.')
rule(r'^decision must be ', 'قرار غير معروف.', 'Unknown decision.')
rule(r'^.+: nothing to decide yet', 'لا يوجد ما تقرره هنا بعد.', 'There is nothing to decide here yet.')
rule(r'^what you reviewed has changed since the page loaded', 'تغيّر المحتوى بعد فتح الصفحة: راجع النسخة الجديدة أولًا.', 'This changed after the page loaded: look at the new version first.',
     {'reload': True, 'label_ar': 'اعرض الجديد', 'label_en': 'Show the new version'})
rule(r'^already (\S+) for this version', 'قررت هذا لهذه النسخة من قبل.', 'You already decided this for this version.')
rule(r'^say what should change', 'اكتب ما الذي يجب أن يتغيّر.', 'Write what should change.', _fix(None, '#note-{gate}', 'خذني للملاحظة', 'Go to the note'))
rule(r'^approve (.+?) \((\S+)\)', lambda m: f'وافق على «{GATE_AR.get(m[2], m[1])}» أولًا.', lambda m: f'Approve {m[1]} first.', None)
rule(r'^the independent research check has not finished', 'فحص البحث المستقل لم ينتهِ بعد. انتظر قليلًا.', 'The independent research check has not finished yet.')
# ---------------------------------------------------------------- voice
rule(r'^to change the voice, tap the word or line', 'لتغيير الصوت: اضغط الكلمة أو السطر وصحّحه (التهجئة، التشكيل، السرعة، الوقفات)، ثم وافق.',
     'To change the voice, tap the word or line and correct it (spelling, tashkeel, speed, pauses), then approve.')
rule(r'^the play-all narration is being rebuilt', 'التسجيل الكامل يُعاد بناؤه لآخر التعديلات: انتظر قليلًا ثم استمع إليه من جديد.',
     'The play-all narration is being rebuilt for the latest takes: wait a moment, then listen again.', _fix('g3', '#mix', 'خذني للتسجيل', 'Go to the narration'))
rule(r'^the play-all narration changed after you listened', 'تغيّر التسجيل الكامل بعد استماعك: استمع إليه من جديد.', 'The play-all narration changed after you listened: listen again.',
     _fix('g3', '#mix', 'خذني للتسجيل', 'Go to the narration'))
rule(r'^listen to every changed line before approving: (.+)', lambda m: f'استمع إلى كل سطر متغيّر قبل الموافقة: {_lines(m[1])}.',
     lambda m: f'Listen to every changed line before approving: {_lines(m[1], lang="en")}.', _fix('g3', '#mix', 'خذني للتسجيل', 'Go to the narration'))
rule(r'^confirm the uncertain words first: (.+)', lambda m: f'قبل الموافقة: استمع إلى {len(m[1].split(","))} كلمة غير واضحة للنسخ الآلي، ثم علّم مربع «استمعتُ إلى هذه الكلمات».',
     lambda m: f'Before approving: listen to the {len(m[1].split(","))} uncertain words, then tick “I listened to these words”.', _fix('g3', '#ackqa', 'خذني للكلمات', 'Go to the words'))
rule(r'^unknown pronunciation entry', 'هذا التصحيح غير موجود.', 'This pronunciation entry does not exist.')
rule(r'^give the word and how the draft voice should read it', 'اكتب كيف تُقرأ الكلمة.', 'Write how the word should be read.', _fix('g3', '#respell', 'خذني للكلمة', 'Go to the word'))
rule(r'^the spelling is the same as the word', 'التهجئة مطابقة للكلمة: غيّر التشكيل أو الحروف.', 'The spelling is the same as the word: change the vowels or letters.', _fix('g3', '#respell', 'خذني للكلمة', 'Go to the word'))
rule(r'^this line has no draft take yet', 'لم يُسجَّل هذا السطر بعد.', 'This line has no draft take yet.')
rule(r'^\w+ must be [\d.]+–[\d.]+', 'القيمة خارج المدى المسموح.', 'The value is out of range.')
rule(r'^unknown take', 'هذا التسجيل غير موجود.', 'This take does not exist.')
# ---------------------------------------------------------------- style
rule(r'^choose one of the styles', 'اختر أسلوبًا.', 'Choose a style.', _fix('g4', '[data-style]', 'خذني للأساليب', 'Go to the styles'))
rule(r'^.+ cannot be used yet: ', 'هذا الأسلوب غير جاهز بعد.', 'This style cannot be used yet.')
# ---------------------------------------------------------------- pictures
rule(r'^upload a file or give a link', 'اختر صورة أو ضع رابطًا.', 'Choose a picture or give a link.', _fix('assets', '#up-file', 'خذني للرفع', 'Go to upload'))
rule(r'^say whether it is a genuine record', 'حدّد: صورة حقيقية (دليل) أم رسم توضيحي.', 'Say whether it is a genuine record or an illustration.')
rule(r'^unknown asset', 'هذه الصورة غير موجودة.', 'This picture does not exist.')
rule(r'^licence must be ', 'اختر نوع الترخيص.', 'Choose the licence type.')
rule(r'^confirm that you own this picture or its rights', 'أكّد أنك تملك الصورة أو حقوقها (المربع تحت الرابط).', 'Confirm that you own this picture or its rights (the box under the link).',
     _fix('assets', '[data-licdec]', 'خذني للإقرار', 'Go to the declaration'))
rule(r'^the licence document must be a file uploaded to this project', 'وثيقة الترخيص يجب أن تكون ملفًا مرفوعًا لهذا المشروع.', 'The licence document must be a file uploaded to this project.')
rule(r'^a picture is not its own licence', 'الصورة نفسها ليست دليل ترخيص: ضع رابط الصفحة التي تذكر الترخيص.', 'A picture is not its own licence: link the page that states the licence.',
     _fix('assets', '[data-licev]', 'خذني للرابط', 'Go to the link'))
rule(r'^licence evidence needed', 'دليل الترخيص مطلوب: ضع رابط الصفحة التي تذكر الترخيص (موقع حقيقي)، أو وثيقة الترخيص.',
     'Licence evidence needed: the page that states the licence (a real site), or the licence document.', _fix('assets', '[data-licev]', 'خذني للرابط', 'Go to the link'))
rule(r"^the picture's own address is not its licence", 'عنوان الصورة نفسه ليس دليل ترخيص: ضع رابط صفحة الترخيص.', "The picture's own address is not its licence: link the licence page.",
     _fix('assets', '[data-licev]', 'خذني للرابط', 'Go to the link'))
rule(r'^the file is empty', 'الملف فارغ.', 'The file is empty.')
rule(r'^the file is larger than 12 MB', 'الملف أكبر من 12 ميقا.', 'The file is larger than 12 MB.')
rule(r'^upload a JPG, PNG or WebP picture', 'ارفع صورة JPG أو PNG أو WebP.', 'Upload a JPG, PNG or WebP picture.')
rule(r'^this file is not a JPG, PNG or WebP picture', 'هذا الملف ليس صورة سليمة: محتواه لا يطابق اسمه.', 'This file is not a real JPG, PNG or WebP picture.')
# ---------------------------------------------------------------- exceptions, comments, findings
rule(r'^say why$', 'اكتب السبب.', 'Write why.')
rule(r'^no open exception with that id', 'هذا القرار لم يعد مفتوحًا.', 'This decision is no longer open.', {'reload': True, 'label_ar': 'حدّث الصفحة', 'label_en': 'Refresh'})
rule(r'^choose one of (?!the styles)', 'اختر أحد الخيارات.', 'Choose one of the options.')
rule(r'^say why you accept it', 'اكتب سبب القبول (يُحفظ في السجل).', 'Write why you accept it (kept in the history).', _fix(None, '#exnote', 'خذني للسبب', 'Go to the reason'))
rule(r'^choose the changes to try', 'اختر تعديلًا واحدًا على الأقل لتجربته.', 'Choose at least one change to try.', _fix(None, '.chips', 'خذني للتعديلات', 'Go to the changes'))
rule(r'^no film to comment on', 'لا يوجد فيلم للتعليق عليه بعد.', 'There is no film to comment on yet.')
rule(r'^comment on the latest film \(v(\d+)\)', lambda m: f'علّق على آخر نسخة من الفيلم (v{m[1]}).', lambda m: f'Comment on the latest film (v{m[1]}).', {'reload': True, 'label_ar': 'اعرض الأحدث', 'label_en': 'Show the latest'})
rule(r'^time code out of range', 'وقت التعليق خارج مدة الفيلم.', 'The comment time is outside the film.')
rule(r'^write the comment', 'اكتب التعليق.', 'Write the comment.', _fix('g5', '#cm', 'خذني للتعليق', 'Go to the comment'))
rule(r'^no open finding with that id', 'هذه الملاحظة لم تعد مفتوحة.', 'This finding is no longer open.', {'reload': True, 'label_ar': 'حدّث الصفحة', 'label_en': 'Refresh'})
rule(r'^a critical finding cannot be dismissed: it must be fixed', 'ملاحظة حرجة: يجب إصلاحها، ولا يمكن إبقاؤها.', 'A critical finding must be fixed; it cannot stay.')
rule(r'^a factual finding can only be overruled with evidence for this scene and a sentence saying why: (.*)',
     lambda m: 'لإبقاء هذه الملاحظة: اكتب دليلًا لهذا المشهد وجملة تشرح السبب ('
               + ('لا يوجد ادعاء مرتبط به، فضع رابط مصدر' if 'no research claim' in m[1] else 'اذكر ' + ' أو '.join(re.findall(r'c\d+', m[1])) + ' أو رابط مصدر') + ').',
     lambda m: 'To keep this finding: give evidence for this scene and a sentence saying why.', _fix('g5', '[data-fexp]', 'خذني للملاحظة', 'Go to the finding'))
rule(r'^say why it can stay', 'اكتب لماذا تبقى (يُحفظ في السجل).', 'Write why it can stay (kept in the history).', _fix('g5', '[data-fexp]', 'خذني للملاحظة', 'Go to the finding'))
# ---------------------------------------------------------------- film
rule(r'^the watching you did was of another draft: watch film v(\d+)', lambda m: f'مشاهدتك كانت لنسخة أخرى: شاهد الفيلم v{m[1]}.', lambda m: f'You watched another draft: watch film v{m[1]}.',
     _fix('g5', '#film', 'خذني للفيلم', 'Go to the film'))
rule(r'^watch the whole draft before approving: (\d+) s of (\d+) s watched', lambda m: f'شاهد المسودة كاملة قبل الموافقة: شاهدت {m[1]} ث من {m[2]} ث.',
     lambda m: f'Watch the whole draft before approving: {m[1]} s of {m[2]} s watched.', _fix('g5', '#film', 'خذني للفيلم', 'Go to the film'))
rule(r'^scenes changed since this film was made: (.+)', lambda m: f'تغيّرت مشاهد بعد صنع هذا الفيلم ({_lines(m[1], True)}): انتظر النسخة الجديدة.',
     lambda m: f'Scenes changed since this film was made ({_lines(m[1], True, "en")}): wait for the new version.')
rule(r'^(\d+) critical or major finding\(s\) are still open', lambda m: f'باقي {m[1]} ملاحظة حرجة أو كبيرة: تُصلح أولًا، أو تُشرح الكبيرة منها.',
     lambda m: f'{m[1]} critical or major finding(s) are still open: fix them, or explain a major one.', _fix('g5', '.finding', 'خذني للملاحظات', 'Go to the findings'))
rule(r'^acknowledge the (\d+) minor issue\(s\) that would remain', lambda m: f'أقرّ بالملاحظات البسيطة الباقية ({m[1]}) بالمربع.',
     lambda m: f'Acknowledge the {m[1]} minor issue(s) that would remain.', _fix('g5', '#ackminor', 'خذني للمربع', 'Go to the box'))
# ---------------------------------------------------------------- paid narration
rule(r'^not authorized: (.+)', lambda m: 'التعليق المدفوع غير مُفوَّض: ' + '؛ '.join(blocker_ar(b) for b in m[1].split('; ')) + '.',
     lambda m: 'Not authorized: ' + m[1] + '.', _fix('g6', '#g6c', 'خذني للخطة', 'Go to the plan'))
rule(r'^paid generation cannot be started from the studio', 'لا يمكن بدء التوليد المدفوع من الاستوديو: البوابة المدفوعة معطّلة في هذه البيئة.',
     'Paid generation cannot be started from the Studio: the paid gateway is disabled here.')

# ---------------------------------------------------------------- paid-plan blockers
B = [
    (r'^build the plan first', 'ابنِ الخطة أولًا'),
    (r'^the plan changed since it was shown', 'تغيّرت الخطة بعد عرضها: راجع الخطة الجديدة'),
    (r'^something changed after this plan was built', 'تغيّر شيء بعد بناء الخطة (الصوت أو الأسماء أو الميزانية أو التسجيلات أو الفيلم): أعد بناءها'),
    (r'^type the number of billable characters \((\d+)\)', lambda m: f'اكتب عدد الأحرف المحسوبة ({m[1]}) للتأكيد'),
    (r'^(.+?) is not a paid text-to-speech voice', lambda m: f'الصوت {m[1]} ليس صوتًا مدفوعًا للقراءة الآلية'),
    (r'^final voice (.+?):', lambda m: f'الصوت النهائي {m[1]} غير جاهز'),
    (r'^script v(\d+) is not approved', lambda m: f'النص v{m[1]} غير موافق عليه'),
    (r'^no draft read was reviewed', 'لم تُراجَع القراءة التجريبية'),
    (r'^(\d+) line\(s\) have no draft take', lambda m: f'{m[1]} سطر بلا تسجيل تجريبي لنصه الحالي'),
    (r'^(\d+) draft line\(s\) not approved', lambda m: f'{m[1]} سطر تجريبي غير موافق عليه'),
    (r'^(\d+) pronunciation flag\(s\) still open', lambda m: f'{m[1]} ملاحظة نطق مفتوحة'),
    (r'^storyboard not approved', 'لوحة المشاهد غير موافق عليها'),
    (r'^hook not selected or its payoff not confirmed', 'الافتتاحية غير مختارة، أو لم يُؤكَّد السطر الذي يحققها'),
    (r'^the latest draft film is not approved', 'آخر مسودة للفيلم غير موافق عليها'),
    (r'^the latest draft film .* has not been checked', 'آخر مسودة للفيلم لم يفحصها المراجع المستقل'),
    (r'^(\d+) review finding\(s\) open', lambda m: f'{m[1]} ملاحظة مراجعة مفتوحة'),
    (r'^(\d+) correction task\(s\) open', lambda m: f'{m[1]} مهمة تصحيح مفتوحة'),
    (r'^art not approved for (.+)', lambda m: f'رسوم غير موافق عليها: {_lines(m[1], True)}'),
    (r'^(\d+) pronunciation entries for the final voice are only proposed', lambda m: f'{m[1]} تصحيح نطق للصوت النهائي مقترح فقط'),
    (r'^no (\S+) budget set for this project', lambda m: f'لا توجد ميزانية {m[1]} لهذا المشروع'),
    (r'^plan needs (\d+) characters, budget has (\S+)', lambda m: f'الخطة تحتاج {m[1]} حرفًا والميزانية {m[2]}'),
    (r'^paid generation is disabled in this environment', 'التوليد المدفوع معطّل في هذه البيئة'),
]
B = [(re.compile(rx), ar) for rx, ar in B]


def blocker_ar(text: str) -> str:
    for rx, ar in B:
        m = rx.search(text or '')
        if m: return ar(m) if callable(ar) else ar
    return 'شرط غير مكتمل (التفاصيل بالإنقليزية في الخطة)'


WHY = [
    (r'^lines changed since you approved the voice: (.+)', lambda m: f'تغيّرت أسطر بعد موافقتك على الصوت: {_lines(m[1])}'),
    (r'^the direction changed', 'تغيّر الاتجاه (نسخة أو إعدادات جديدة)'),
    (r'^a newer script version exists', 'توجد نسخة أحدث من النص'),
    (r'^new style boards were drawn', 'رُسمت لوحات أسلوب جديدة'),
    (r'^the film changed', 'تغيّر الفيلم'),
    (r'^the paid plan changed', 'تغيّرت خطة التعليق المدفوع'),
    (r'^depends on (.+), which is no longer approved', lambda m: 'يعتمد على ' + '، '.join(GATE_AR.get(g.strip(), g) for g in m[1].split(',')) + '، ولم تعد موافقتها سارية'),
    (r'^what it was built on was approved again with different content', 'ما بُني عليه وافقتَ عليه من جديد بمحتوى مختلف'),
    (r'^paid narration is locked in this workspace', 'التعليق المدفوع مقفل في هذه البيئة'),
    (r'^needs the paid narration, then a master approval', 'يحتاج التعليق المدفوع ثم موافقة نهائية؛ النشر تفويض منفصل ولا يحدث تلقائيًا'),
]
WHY = [(re.compile(rx), ar) for rx, ar in WHY]


def why_ar(text):
    if not text: return text
    for rx, ar in WHY:
        m = rx.search(text)
        if m: return ar(m) if callable(ar) else ar
    e = explain(text)
    return e['ar'] if e['known'] else text


TITLES = [
    (r'^Scene (\S+): a factual problem on screen', lambda m: f'{line_ar(m[1], True)}: مشكلة في معلومة على الشاشة'),
    (r'^Scene (\S+): a fix would change something you approved', lambda m: f'{line_ar(m[1], True)}: الإصلاح يغيّر شيئًا وافقتَ عليه'),
    (r'^Scene (\S+): a problem the Co-Pilot cannot fix safely', lambda m: f'{line_ar(m[1], True)}: مشكلة لا يستطيع المساعد إصلاحها بأمان'),
    (r'^Scene (\S+): still not right after (\d+) correction round', lambda m: f'{line_ar(m[1], True)}: ما زال غير مضبوط بعد {m[2]} جولة تصحيح'),
    (r'^Scene (\S+) needs you', lambda m: f'{line_ar(m[1], True)} يحتاجك'),
    (r'^Picture «(.+)» has no licence evidence', lambda m: f'الصورة «{m[1]}» بلا دليل ترخيص'),
    (r'^The AI could not make the change you asked for', 'لم يستطع الذكاء تنفيذ التعديل الذي طلبته'),
    (r'^The AI could not research this idea', 'لم يستطع الذكاء البحث في هذه الفكرة'),
    (r'^Your comment needs a person: «(.+)»', lambda m: f'تعليقك يحتاج شخصًا: «{m[1]}»'),
    (r'^A different style needs a person', 'أسلوب مختلف يحتاج شخصًا'),
    (r'^Your note on the film needs a person', 'ملاحظتك على الفيلم تحتاج شخصًا'),
    (r'^(.+) failed$', lambda m: f'تعذّرت خطوة: {m[1]}'),
]
TITLES = [(re.compile(rx), ar) for rx, ar in TITLES]


def title_ar(text):
    for rx, ar in TITLES:
        m = rx.search(text or '')
        if m: return ar(m) if callable(ar) else ar
    return text


def explain(reason: str, action: str | None = None, args: dict | None = None) -> dict:
    reason = (reason or '').strip()
    gate = (args or {}).get('gate')
    for rx, ar, en, fix in R:
        m = rx.search(reason)
        if not m: continue
        out = {'ar': ar(m) if callable(ar) else ar, 'en': en(m) if callable(en) else en, 'known': True, 'fix': None}
        if fix:
            f = dict(fix)
            if f.get('target') and '{gate}' in f['target']:
                f['target'] = f['target'].replace('{gate}', gate or '')
            if not f.get('reload') and not f.get('panel') and gate:
                f['panel'] = GATE_PANEL.get(gate)
            out['fix'] = f
        return out
    return {'ar': 'تعذّر تنفيذ هذا الطلب.', 'en': 'This could not be done.', 'known': False, 'fix': None}
