# تثبيت تطبيق مكتب المحاماة (macOS) — DMG

دليل التثبيت اليدوي على Mac. الملف موجود تحت :

```
dist/AvocatDesktop.dmg
```

## نظرة سريعة
- حجم DMG : ~53 MB (مضغوط) → ~110 MB بعد التثبيت
- macOS 11 (Big Sur) فما فوق
- لا يحتاج اتصالاً بالإنترنت إلا للوصول لخادم المكتب
- غير موقّع بشهادة Apple بعد (انظر "تحذيرات Gatekeeper" أدناه)

---

## التثبيت

1. **افتح DMG** بنقرة مزدوجة. تظهر نافذة فيها أيقونة `AvocatDesktop.app`
   وأخرى `Applications`.
2. **اسحب** `AvocatDesktop.app` إلى مجلد `Applications`.
3. أغلق النافذة، ثم أخرج DMG من Finder (يمين على الأيقونة على سطح المكتب → "إخراج").
4. شغّل التطبيق من Launchpad أو من `Applications/`.

---

## تحذيرات Gatekeeper (التطبيقات غير الموقّعة)

عند أول تشغيل ستظهر رسالة :

> «Cannot open AvocatDesktop because the developer cannot be verified»

هذا طبيعي لأن DMG ليس موقّعاً بشهادة Apple Developer ($99/year).

**للسماح يدوياً** :

1. Finder → `Applications` → كليك يمين على `AvocatDesktop.app` → **Open**.
2. تظهر النافذة نفسها ولكن مع زر **Open** إضافي. اضغطه.
3. macOS يحفظ الاستثناء — المرّات اللاحقة ستفتح مباشرة.

أو عبر سطر الأوامر :
```bash
xattr -dr com.apple.quarantine /Applications/AvocatDesktop.app
```

---

## التشغيل الأول

أول إطلاق ينشئ المجلد :

```
~/.avocat_desktop/
├── local.sqlite3        # نسخة محلية مرآة للخادم
├── media/               # الملفات المرفقة (PieceJointe)
├── secret.key           # مفتاح Django لهذا التثبيت
├── credentials.json     # بيانات JWT للمزامنة (اكتبها يدوياً أول مرّة)
├── launcher.log         # سجل الإقلاع
└── desktop.log          # سجل وقت التشغيل
```

**إعداد بيانات المزامنة** عند أول تشغيل :

أنشئ `~/.avocat_desktop/credentials.json` بصيغة :
```json
{
  "username": "اسم_المستخدم_على_الخادم",
  "password": "كلمة_المرور_على_الخادم"
}
```

ثم اضغط زرّ **مزامنة** في شريط التنقل لجلب البيانات أوّل مرّة.

(بديل : افتح `http://127.0.0.1:<port>/desktop/setup/` داخل التطبيق نفسه
لإدخال البيانات عبر نموذج.)

---

## التحديث

نزّل DMG الجديد، اسحب التطبيق إلى `Applications` فوق القديم (يستبدله).
بيانات `~/.avocat_desktop/` تبقى — لا تُفقد عند التحديث.

---

## استكشاف الأخطاء

| المشكلة | السبب الأرجح | الحل |
|---|---|---|
| التطبيق لا يفتح | Gatekeeper يمنعه | اتبع تعليمات Gatekeeper أعلاه |
| شاشة بيضاء بعد التشغيل | Django لم يكتمل بدء التشغيل بعد | انتظر 5 ثوان، أعد فتح التطبيق |
| "Already running" | إصدار سابق ما زال يحجز منفذاً | `pkill -f AvocatDesktop` ثم أعد التشغيل |
| فشل المزامنة | الخادم غير متاح أو credentials.json خاطئ | راجع `~/.avocat_desktop/desktop.log` |
| لا توجد بيانات | لم تشغّل أول مزامنة | اضغط زرّ المزامنة في شريط التنقل |

---

## إزالة كاملة

```bash
rm -rf /Applications/AvocatDesktop.app
rm -rf ~/.avocat_desktop                # ⚠️ يحذف البيانات المحلية
```

---

## للنشر العمومي (التوقيع والتوثيق)

عند الجاهزية للتوزيع :

1. **شهادة Apple Developer ID** (~$99/سنة).
2. وقّع التطبيق :
   ```
   codesign --force --deep --options runtime \
     --sign "Developer ID Application: Your Name (TEAMID)" \
     dist/AvocatDesktop.app
   ```
3. وثّقه عند Apple :
   ```
   ditto -c -k --keepParent dist/AvocatDesktop.app AvocatDesktop.zip
   xcrun notarytool submit AvocatDesktop.zip \
     --apple-id you@example.com --team-id TEAMID \
     --password app-specific-password --wait
   xcrun stapler staple dist/AvocatDesktop.app
   ```
4. أعد بناء DMG بعد ذلك بنفس الأمر :
   ```
   hdiutil create -volname "AvocatDesktop" \
     -srcfolder dist/AvocatDesktop.app -ov -format UDZO \
     dist/AvocatDesktop.dmg
   ```
