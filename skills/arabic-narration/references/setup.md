# الإعداد، والنماذج، والترخيص

## البيئة (CPU يكفي)
```bash
python3.11 -m venv tts_f && . tts_f/bin/activate
pip install "coqui-tts[codec]==0.27.5" "transformers==4.57.3" faster-whisper pyyaml
pip install --force-reinstall "torch==2.8.0" "torchaudio==2.8.0" --index-url https://download.pytorch.org/whl/cpu   # coqui يسحب نسخة أحدث؛ أرجعها
# ffmpeg لازم يكون موجود في النظام
```
- النماذج تنزل تلقائياً في أول تشغيل (مجانية من Hugging Face):
  - `NightPrince/Fasih-TTS-V1` (1.9GB).
  - Whisper `medium`.
  - `facebook/wav2vec2-xlsr-53-espeak-cv-ft`.
- **CATT (اختياري، رأي ثاني فقط):** `pip install --target <dir> catt-tashkeel onnxruntime`، ثم `ARABIC_TTS_CATT_PATH=<dir>`. ينزّل نماذجه أول مرة.
  - لا تثبّت onnxruntime داخل بيئة الصوت إذا كان سيغيّر نسخة numpy.
- **الأداء على المعالج:**
  - المحاولة الواحدة تأخذ 6 إلى 40 ث حسب طول السطر.
  - المرحلة 3 تضيف تحليل Whisper والفونيمات لكل محاولة.
  - حلقة 30 سطراً تأخذ حوالي ساعة إلى ساعتين.
  - شغّلها في الخلفية، وانتظر الانتهاء بأمر ينتهي عند الشرط (`until grep -q 'RUN DONE' …`)، لا بحلقات sleep قصيرة.
- **القرص:** النماذج مع الكاش أكثر من 6GB. احذف ملفات `cache/` القديمة بعد التسليم إذا ضاق المكان.

## الصوت المرجعي
- مقطع نظيف مدته 10 إلى 15 ثانية بالصوت المطلوب، بلا موسيقى (`ARABIC_TTS_REF`).
- الإعدادات ثابتة في `engine.py`:
  - الحرارة 0.72/0.62/0.8 بالتناوب.
  - repetition_penalty 2.0.
  - السرعة 1.12.
  - top_p 0.9.
  - top_k 60.
- لا تغيّر الإعدادات إلا بطلب صريح، فالمستخدم اعتمد الصوت بها.
- ⛔ لا تمطّط الصوت (rubberband أو atempo) لتبطئه، فيصير آلياً.

## الترخيص (نبّه قبل أي استخدام تجاري)
| العنصر | الرخصة | الاستخدام التجاري |
|---|---|---|
| Fasih-TTS-V1 (مشتق XTTS v2) | Coqui Public Model License | **غير تجاري فقط**، ويشمل الصوت الناتج. أي دخل مباشر أو غير مباشر يُعتبر تجارياً. لا جهة تبيع رخصة تجارية بعد إغلاق Coqui |
| مكتبة coqui-tts | MPL-2.0 | مسموح |
| صوت مرجعي من ElevenLabs أو غيره | شروط الخدمة | المجاني غير تجاري. استخدامه مرجعاً في محرك آخر غير محسوم، ويحتاج مراجعة قانونية |
| Whisper، wav2vec2، CATT (الكود) | MIT / Apache | للتقييم فقط، ولا تدخل في الصوت الناتج |
