# خط العمل بالتفصيل

## صيغ الملفات
- `script.min.json`: الكابشن، `[{"id":"l1","text":"…","gap_after":0.3,"scene":"a1"}, …]`.
  - قيم `gap_after`: 0.3 داخل المشهد، و0.8 آخر سطر في المشهد، و1.0 قبل كرت النهاية.
- `script_d.json`: نص الكاتب بحركاته إن وُجدت، `[{"id":"l1","d":"…","text":"…"}]`. الحركات التي يكتبها الكاتب لها الأولوية.
- `proposals.json`: تشكيل كامل تكتبه أنت لكل سطر، `{"l1":"كَبِرَتْ إِلِيزَابِيث… وَصَارَتْ زَوْجَةً وَأُمًّا…"}`.
- `overrides.json`: تعديلات على النص المنطوق فقط، `{"l22":[{"from":"جِدًّا…","to":"جِدًّا،"}]}`.

## كتابة التشكيل الكامل (proposals)
- **شكّل كل حرف مع الإعراب،** بما فيه آخر الكلمة قبل علامة الوقف: الموديل تدرّب على نص مشكّل بالكامل.
- **الحروف تبقى كما هي حرفاً بحرف،** بما فيها الهمزات وعلامات الترقيم. أي اختلاف = FAIL.
- **الأمور اللي تحتاج انتباه:**
  - المبني للمجهول (كُتِبَ، يُعْطَى، اكْتُشِفَ).
  - الممنوع من الصرف بعد حرف جر (بِلَنْدَنَ، أَطِبَّاءَ، أَكْبَرَ).
  - المضاف إليه (تَسْجِيلَ طَرِيقَتِهِمَا).
  - همزة الوصل بعد ساكن (إِذَنِ المُشْكِلَةُ، نَالَتِ العَالِمَةُ).
  - المنقوص (تَحَدٍّ).
  - التمييز (كَمْ جُرْعَةً).
  - «كَبِرَ» في السن مقابل «كَبُرَ» في الحجم.
  - «العَشَاء» الوجبة مقابل «العِشَاء» الصلاة.
- **الأسماء الأجنبية:** اترك آخرها بلا حركة (`ending: fixed` في القاموس).
- **بعد التشغيل:** اقرأ خلافات CATT كلها، وغيّر فقط ما تتأكد أنه زلّة منك.

## الأوامر
```bash
cd <proj>
export PYTHONPATH=<skill>/scripts ARABIC_TTS_REF=<ref.wav> ARABIC_TTS_WORK=$PWD/tts_work ARABIC_TTS_LEXICON=$PWD/tts_work/lexicon.yaml
# اختياري: CATT خارج بيئة الصوت
export ARABIC_TTS_CATT_PATH=<dir-with-catt_tashkeel>:<dir-with-onnxruntime>

python -m arabic_tts.lexicon check $ARABIC_TTS_LEXICON
python -m arabic_tts.diacritize script_d.json proposals.json tts_work/full.json --lexicon $ARABIC_TTS_LEXICON
python -m arabic_tts.lexicon apply $ARABIC_TTS_LEXICON tts_work/full.json tts_work/p12.json
python -m arabic_tts.preprocess tts_work/p12.json tts_work/ready.json [--overrides overrides.json]
nohup python -m arabic_tts.run tts_work/ready.json tts_work/run.json --select phase3 > tts_work/run.log 2>&1 &
python -m arabic_tts.assemble tts_work/run.json script.min.json tts_work/review/new --tts-texts tts_work/ready.json
python -m arabic_tts.review.build tts_work/review/review.html "new|الحلقة 7|tts_work/review/new" --title "مراجعة نطق الحلقة 7"
```
- **`--on-conflict proposal`:** يطبّق تشكيلك بدل حركة الكاتب. لا تستخدمه إلا بعد موافقة الكاتب على التصحيح، مثل «طَرِيقَتِهِمَا» بدل «طَرِيقَتَهُمَا».
- **`run.py --select baseline`:** يعيد الاختيار القديم (Whisper فقط). استخدمه للمقارنة العادلة: المحاولات تأخذ بذوراً ثابتة (1000+k)، والكاش يشارك الصوت بين الطرفين.
- **`run.json`:** لكل سطر يحفظ المحاولات (`takes`)، والمختارة (`chosen`)، والملاحظات (`flags`)، و`uncertain`.

## إعادة توليد أسطر بعد المراجعة
1. عدّل `script.min.json` و`script_d.json` و`proposals.json` للأسطر المتغيّرة، وأعد تشغيل diacritize.
2. اعمل ملف عناصر فيه **الأسطر المعلّمة فقط**، ثم lexicon ← preprocess ← run بملف جديد (`fix1/run.json`).
   - إذا كان النص نفسه لم يتغيّر، فالمحاولة نفسها سترجع من الكاش. أضف للسطر `"reject_takes": [رقم المحاولة المرفوضة]` ليبدأ من بذور جديدة.
   - إذا كان الخطأ صوتاً محدداً يتغيّر من محاولة لأخرى (همزة، حرف)، ابحث عنه مباشرة: ولّد محاولات جديدة حتى تظهر الفونيمات المطلوبة (مثل `ʔil` أو `^kab`)، ثم اختر بيدك وسجّل السبب في `flags`.
3. ادمج: `{**run_v1, **fix1}`، ثم assemble إلى مجلد جديد (`new2`). علّم الأسطر المصححة بـ`fixed: true` في timing.json، والصفحة تعرض لها شارة «مصحح».
4. ابنِ الصفحة بكل النسخ (`new2` أولاً، ثم `new`، ثم المرجع)، وانشرها على **نفس الملف** حتى يبقى الرابط نفسه.

## التسليم للفيديو
- مخرجات `assemble` (ملفات `vo/<id>.wav` المنظفة والمبطّنة 0.12/0.1 ث، ومعها التوقيتات) تصلح مباشرة للتايملاين.
- في محرك video-ad-editor: انسخها إلى `<part>/vo/` مع `words.json` ثم شغّل `timeline.py`.
- التنظيف بـ`scripts/arabic_tts/voice_clean.sh`: ffmpeg، 44.1kHz، إزالة طقطقة، ضغط، وloudnorm -16.
